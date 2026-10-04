"""Send a REQUEST that carries the stage specification, requirements and contracts in full.

The specification is copied from the human's dispatch in the room, the requirements from the
record and the contracts from spec/, so nothing is retyped or summarised on the way.

    python scripts/handoff.py --seat lead --room ROOM --to builder --stage 1 \
        --req S1-R1,S1-R2 --due 120 --note "Build stage 1 in stage-1/."

Long requests go out as numbered parts; the last is marked "final part".
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

from seat import refuse_unless

ROOT = pathlib.Path(__file__).resolve().parent.parent
BAND = os.path.expandvars(r"%LOCALAPPDATA%\Band\band.exe")
PART = 20000
SPEC_MARK = re.compile(r"^Stage (\d+) specification, complete and verbatim:\s*$", re.MULTILINE)


def band(*args):
    result = subprocess.run([BAND, *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        sys.exit(f"band {args[0]} failed: {(result.stdout + result.stderr).strip()}")
    return result.stdout


def dispatched_spec(room, stage):
    for page in range(1, 50):
        result = json.loads(band("room", "messages", room, "--type", "text", "--json",
                                 "--page", str(page)) or "{}")
        for row in result.get("messages") or []:
            if row.get("sender_type") == "Agent":
                continue
            content = row.get("content") or ""
            marks = list(SPEC_MARK.finditer(content))
            for found, after in zip(marks, marks[1:] + [None]):
                if int(found.group(1)) == stage:
                    return content[found.end():after.start() if after else None].strip()
        if not result.get("has_more"):
            break
    sys.exit(f"no human dispatch carrying the stage {stage} specification found in room {room}")


def participant_handle(room, seat):
    for line in band("room", "participants", room).splitlines():
        found = re.match(rf"(\S+/{seat}) \[", line)
        if found:
            return found.group(1)
    sys.exit(f"seat {seat} is not in room {room}; add it first")


def requirements(stage, wanted):
    rows = []
    for path in sorted((ROOT / "record").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("type") == "requirement" and str(row.get("stage")) == str(stage):
                    rows.append(row)
    if wanted:
        rows = [r for r in rows if r["id"] in wanted]
    missing = set(wanted) - {r["id"] for r in rows}
    if missing:
        sys.exit(f"not in the record: {', '.join(sorted(missing))}")
    return "\n".join(f"- {r['id']} ({r.get('source', '')}): {r['text']}" for r in rows)


def contracts():
    files = sorted(p for p in (ROOT / "spec").rglob("*") if p.is_file() and p.name != ".gitkeep")
    return "\n\n".join(f"### {p.relative_to(ROOT).as_posix()}\n\n{p.read_text(encoding='utf-8').strip()}"
                       for p in files) or "(none written)"


def split(text):
    parts, current = [], ""
    for block in re.split(r"(\n\n)", text):
        while len(block) > PART:
            parts.append(current + block[:PART - len(current)])
            block, current = block[PART - len(current):], ""
        if len(current) + len(block) > PART:
            parts.append(current)
            current = ""
        current += block
    return parts + [current] if current.strip() else parts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seat", required=True)
    parser.add_argument("--room", required=True)
    parser.add_argument("--to", required=True)
    parser.add_argument("--stage", required=True, type=int)
    parser.add_argument("--req", default="", help="requirement ids; default: every one for the stage")
    parser.add_argument("--due", required=True, type=int, help="minutes")
    parser.add_argument("--note", default="", help="what this seat is asked to do")
    parser.add_argument("--dry-run", action="store_true", help="print the parts instead of sending")
    args = parser.parse_args()
    seat, to = args.seat.lower(), args.to.lower()
    refuse_unless(seat, "send")

    wanted = [r.strip() for r in args.req.split(",") if r.strip()]
    reqs = requirements(args.stage, wanted)
    body = "\n\n".join([
        f"Result repository (absolute path): {ROOT}",
        f"Stage folder: stage-{args.stage}/",
        args.note.strip(),
        f"## Requirements\n\n{reqs}",
        f"## Contracts\n\n{contracts()}",
        f"## Stage {args.stage} specification, complete and verbatim\n\n"
        f"{dispatched_spec(args.room, args.stage)}",
    ])
    req_ids = ",".join(wanted) if wanted else "all"
    parts = split(body)
    mention = "" if args.dry_run else f"@{participant_handle(args.room, to)}"
    for number, part in enumerate(parts, 1):
        label = "final part" if number == len(parts) else "more parts follow"
        text = (f"{mention} REQUEST stage={args.stage} req={req_ids} due={args.due} "
                f"part={number}/{len(parts)}\n{label.capitalize()}.\n\n{part.strip()}\n")
        if args.dry_run:
            print(f"----- part {number}/{len(parts)}: {len(text)} characters\n{text[:600]}")
        else:
            band("--session", f"umbra-{seat}", "send", args.room, text)
            print(f"sent part {number}/{len(parts)} to {to} ({len(text)} characters)")


if __name__ == "__main__":
    main()
