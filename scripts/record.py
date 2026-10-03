"""The band's shared record: requirements, rulings, checks, evidence, verdicts.

Append-only, one JSONL file per seat under record/, raw output under evidence/<seat>/.
Status is derived from the files at the current revision, never stored.

    python scripts/record.py requirement --seat lead --id S1-R1 --stage 1 --source "spec line" --text "..."
    python scripts/record.py ruling      --seat lead --id S1-U1 --req S1-R1 --text "..."
    python scripts/record.py check       --seat verifier --id S1-C1 --req S1-R1,S1-R2 --text "..."
    python scripts/record.py evidence    --seat verifier --check S1-C1 --run "python scripts/lever.py checks --suite verifier --stage 1"
    python scripts/record.py verdict     --seat verifier --kind ACCEPT --stage 1 --rev REV --ev E-verifier-3
    python scripts/record.py cost        --seat lead --usd 1.25 --note "band usage"
    python scripts/record.py status      [--stage 1]
    python scripts/record.py stale
    python scripts/record.py show        --id E-verifier-3
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

from seat import refuse_unless

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORD = ROOT / "record"
EVIDENCE = ROOT / "evidence"
REVIEWERS = {"verifier", "breaker", "uireviewer", "certifier", "endurance"}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def head():
    """The last commit that changed product code. Record and test commits do not move it."""
    result = subprocess.run(["git", "log", "-1", "--format=%H", "--", "stage-*"], cwd=ROOT,
                            capture_output=True, text=True)
    return result.stdout.strip()[:12] or "none"


def dirty():
    result = subprocess.run(["git", "status", "--porcelain", "--", "stage-*"],
                            cwd=ROOT, capture_output=True, text=True)
    return bool(result.stdout.strip())


def entries():
    rows = []
    for path in sorted(RECORD.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append(seat, row):
    RECORD.mkdir(exist_ok=True)
    row = {"type": row.pop("type"), "seat": seat, "at": now(), **row}
    with (RECORD / f"{seat}.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def ids(text):
    return [part.strip() for part in (text or "").split(",") if part.strip()]


def next_evidence_id(seat):
    count = sum(1 for r in entries() if r["type"] == "evidence" and r["seat"] == seat)
    return f"E-{seat}-{count + 1}"


def lead_only(a, what):
    if a.seat != "lead":
        sys.exit(f"{what} are Lead's; record a check instead, or ask Lead in the room")


def cmd_requirement(a):
    lead_only(a, "requirements")
    print(append(a.seat, {"type": "requirement", "id": a.id, "stage": a.stage,
                          "source": a.source, "text": a.text})["id"])


def cmd_ruling(a):
    lead_only(a, "rulings")
    print(append(a.seat, {"type": "ruling", "id": a.id, "req": ids(a.req), "text": a.text})["id"])


def cmd_withdraw(a):
    lead_only(a, "withdrawals")
    if not any(r["type"] == "check" and r["id"] == a.check for r in entries()):
        sys.exit(f"no check {a.check}")
    print(append(a.seat, {"type": "withdrawal", "check": a.check, "text": a.text})["check"])


def cmd_check(a):
    owner = next((r["seat"] for r in entries() if r["type"] == "check" and r["id"] == a.id), None)
    if owner and owner != a.seat:
        sys.exit(f"check {a.id} already belongs to {owner}; choose an identifier of your own")
    print(append(a.seat, {"type": "check", "id": a.id, "req": ids(a.req), "text": a.text})["id"])


def cmd_evidence(a):
    known = {r["id"] for r in entries() if r["type"] == "check"}
    if a.check not in known:
        sys.exit(f"record the check {a.check} first")
    evidence_id = next_evidence_id(a.seat)
    folder = EVIDENCE / a.seat
    folder.mkdir(parents=True, exist_ok=True)
    revision, was_dirty = head(), dirty()
    started = time.monotonic()
    try:
        result = subprocess.run(a.run, shell=True, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=a.timeout)
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        code, output = 124, f"{exc.stdout or ''}{exc.stderr or ''}\ntimed out after {a.timeout}s"
    seconds = round(time.monotonic() - started, 1)
    log = folder / f"{evidence_id}.log"
    log.write_text(f"$ {a.run}\n{output}\nexit {code}\n", encoding="utf-8", newline="\n")
    digest = hashlib.sha256(output.encode("utf-8")).hexdigest()[:16]
    append(a.seat, {"type": "evidence", "id": evidence_id, "check": a.check, "run": a.run,
                    "rev": revision, "dirty": was_dirty, "exit": code, "seconds": seconds,
                    "sha": digest, "log": log.relative_to(ROOT).as_posix()})
    tail = "\n".join(output.strip().splitlines()[-15:])
    print(f"{tail}\n{evidence_id} check={a.check} rev={revision}{' (dirty)' if was_dirty else ''} "
          f"exit={code} log={log.relative_to(ROOT).as_posix()}")
    sys.exit(0 if code == 0 else 1)


def cmd_verdict(a):
    known = {r["id"]: r for r in entries() if r["type"] == "evidence"}
    for evidence_id in ids(a.ev):
        row = known.get(evidence_id)
        if not row:
            sys.exit(f"unknown evidence {evidence_id}")
        same_rev = row["rev"].startswith(a.rev) or a.rev.startswith(row["rev"])
        if a.kind == "ACCEPT" and (row["seat"] != a.seat or not same_rev or row["exit"]
                                   or row["dirty"]):
            sys.exit(f"{evidence_id} cannot back ACCEPT: it must be yours, at {a.rev}, and passing")
    if a.kind == "SEAL":
        if a.seat != "certifier":
            sys.exit("only Certifier seals a stage")
        states, verified = coverage(entries(), a.stage, a.rev)
        if verified < len(states) or not states:
            open_ = [f"{req} {state}" for req, state in states if state != "verified"]
            sys.exit(f"cannot SEAL stage {a.stage} at {a.rev}: {verified}/{len(states)} "
                     f"requirements verified. Open: " + "; ".join(open_))
    print(append(a.seat, {"type": "verdict", "kind": a.kind, "stage": a.stage, "rev": a.rev,
                          "ev": ids(a.ev), "note": a.note or ""})["kind"])


def cmd_cost(a):
    append(a.seat, {"type": "cost", "usd": a.usd, "note": a.note or ""})
    print(f"{sum(r['usd'] for r in entries() if r['type'] == 'cost'):.2f} total")


def same_revision(a, b):
    return bool(a and b) and (a.startswith(b) or b.startswith(a))


def latest_evidence(rows, revision):
    """The latest clean run of each check at `revision`, by the seat that owns the check."""
    owner = {r["id"]: r["seat"] for r in rows if r["type"] == "check"}
    best = {}
    for row in rows:
        if (row["type"] == "evidence" and same_revision(row["rev"], revision)
                and not row["dirty"] and owner.get(row["check"]) == row["seat"]):
            best[row["check"]] = row
    return best


def coverage(rows, stage, revision):
    """Per requirement: verified only when every reviewer check covering it passed at
    `revision` in its owner's own latest run. Builder's self-run checks do not count."""
    requirements = [r for r in rows if r["type"] == "requirement"
                    and (stage is None or str(r["stage"]) == str(stage))]
    withdrawn = {r["check"] for r in rows if r["type"] == "withdrawal"}
    checks = [r for r in rows if r["type"] == "check" and r["seat"] in REVIEWERS
              and r["id"] not in withdrawn]
    evidence = latest_evidence(rows, revision)
    states, verified = [], 0
    for requirement in requirements:
        covering = [c for c in checks if requirement["id"] in c["req"]]
        runs = {c["id"]: evidence.get(c["id"]) for c in covering}
        failing = [r["id"] for r in runs.values() if r and r["exit"] != 0]
        unrun = [check for check, r in runs.items() if not r]
        if failing:
            state = "FAILING " + ",".join(failing)
        elif not covering:
            state = "NO CHECK"
        elif unrun:
            state = "unrun at this revision: " + ",".join(unrun)
        else:
            state, verified = "verified", verified + 1
        states.append((requirement["id"], state))
    return states, verified


def cmd_status(a):
    revision = a.rev or head()
    states, verified = coverage(entries(), a.stage, revision)
    for requirement, state in states:
        print(f"{requirement:<10} {state}")
    print(f"rev={revision} verified {verified}/{len(states)}")
    sys.exit(0 if states and verified == len(states) else 1)


def cmd_stale(a):
    revision = head()
    for row in entries():
        if row["type"] == "evidence" and row["rev"] != revision:
            print(f"{row['id']} check={row['check']} rev={row['rev']} (head {revision})")


def cmd_show(a):
    for row in entries():
        if row.get("id") == a.id:
            print(json.dumps(row, indent=2, ensure_ascii=False))
            return
    sys.exit(f"no record entry {a.id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(__doc__.splitlines()[4:]))
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, handler, *fields):
        p = sub.add_parser(name)
        for field, required in fields:
            p.add_argument(f"--{field}", required=required)
        p.set_defaults(handler=handler)
        return p

    add("requirement", cmd_requirement, ("seat", True), ("id", True), ("stage", True),
        ("source", True), ("text", True))
    add("ruling", cmd_ruling, ("seat", True), ("id", True), ("req", False), ("text", True))
    add("check", cmd_check, ("seat", True), ("id", True), ("req", True), ("text", True))
    add("withdraw", cmd_withdraw, ("seat", True), ("check", True), ("text", True))
    p = add("evidence", cmd_evidence, ("seat", True), ("check", True), ("run", True))
    p.add_argument("--timeout", type=int, default=900)
    p = add("verdict", cmd_verdict, ("seat", True), ("stage", True), ("rev", True),
            ("ev", False), ("note", False))
    p.add_argument("--kind", required=True, choices=["ACCEPT", "REJECT", "SEAL"])
    p = add("cost", cmd_cost, ("seat", True), ("note", False))
    p.add_argument("--usd", type=float, required=True)
    add("status", cmd_status, ("stage", False), ("rev", False))
    add("stale", cmd_stale)
    add("show", cmd_show, ("id", True))
    args = parser.parse_args()
    if hasattr(args, "seat") and args.seat:
        args.seat = args.seat.lower()
        refuse_unless(args.seat, "record")
    args.handler(args)


if __name__ == "__main__":
    main()
