"""Generate stage-2 mutant patches (certifier-owned)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WT = ROOT / ".umbra" / "patch-gen-s2"
MUT = ROOT / "mutants" / "stage-2"
REV = "b013f5e17143"


def run(*args, cwd=ROOT):
    subprocess.run(list(args), cwd=cwd, check=True)


def write_patch(name: str, *paths: str):
    out = subprocess.run(
        ["git", "diff", "--", *paths],
        cwd=WT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if out.returncode != 0 or not out.stdout.strip():
        sys.exit(f"empty diff for {name}")
    (MUT / name).write_text(out.stdout, encoding="utf-8", newline="\n")
    print(name, "ok", len(out.stdout), "bytes")


def main():
    MUT.mkdir(parents=True, exist_ok=True)
    if WT.exists():
        subprocess.run(["git", "worktree", "remove", "-f", str(WT)], cwd=ROOT, check=False)
    run("git", "worktree", "add", str(WT), REV, "--detach")

    hf = WT / "stage-2" / "handlers.go"
    run("git", "checkout", "--", "stage-2/handlers.go", cwd=WT)
    t = hf.read_text(encoding="utf-8-sig")
    hf.write_text(
        t.replace(
            "if sv.store.availableForUserLocked(from.ID) < amount {",
            "if false && sv.store.availableForUserLocked(from.ID) < amount {",
            1,
        ),
        encoding="utf-8",
        newline="\n",
    )
    write_patch("m01_skip_available_balance.patch", "stage-2/handlers.go")

    af = WT / "stage-2" / "authorization.go"
    run("git", "checkout", "--", "stage-2/authorization.go", cwd=WT)
    t = af.read_text(encoding="utf-8-sig")
    old = "\treturn held\n}\n\nfunc (s *Store) availableForUserLocked"
    new = "\treturn 0\n}\n\nfunc (s *Store) availableForUserLocked"
    if old not in t:
        sys.exit("heldForUser pattern missing")
    af.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
    write_patch("m02_ignore_holds.patch", "stage-2/authorization.go")

    idf = WT / "stage-2" / "idempotency.go"
    run("git", "checkout", "--", "stage-2/idempotency.go", cwd=WT)
    t = idf.read_text(encoding="utf-8-sig")
    idf.write_text(
        t.replace(
            "\trec, ok := s.Idempotency[fullKey]",
            "\tdelete(s.Idempotency, fullKey)\n\trec, ok := s.Idempotency[fullKey]",
            1,
        ),
        encoding="utf-8",
        newline="\n",
    )
    write_patch("m03_idempotency_no_replay.patch", "stage-2/idempotency.go")

    subprocess.run(["git", "worktree", "remove", "-f", str(WT)], cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
