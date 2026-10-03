"""Generate mutant patches from detached worktree (certifier-owned script)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WT = ROOT / ".umbra" / "patch-gen"
MUT = ROOT / "mutants" / "stage-1"


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


def edit_handlers(old: str, new: str):
    hf = WT / "stage-1" / "handlers.go"
    text = hf.read_text(encoding="utf-8-sig")
    if old not in text:
        sys.exit("handlers pattern missing")
    hf.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def edit_idempotency(old: str, new: str):
    p = WT / "stage-1" / "idempotency.go"
    text = p.read_text(encoding="utf-8-sig")
    if old not in text:
        sys.exit("idempotency pattern missing")
    p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


ACTIVITY_OLD = """\tvar visible []Payment
\tfor _, p := range sv.store.Payments {
\t\tif p.Visibility == \"public\" || p.FromUserID == u.ID || p.ToUserID == u.ID {
\t\t\tvisible = append(visible, p)
\t\t}
\t}"""

ACTIVITY_NEW = """\tvar visible []Payment
\tfor _, p := range sv.store.Payments {
\t\tif p.FromUserID != u.ID && p.ToUserID != u.ID {
\t\t\tpairPrivate := false
\t\t\tfor _, q := range sv.store.Payments {
\t\t\t\tif q.Visibility != \"private\" {
\t\t\t\t\tcontinue
\t\t\t\t}
\t\t\t\tif (p.FromUserID == q.FromUserID && p.ToUserID == q.ToUserID) ||
\t\t\t\t\t(p.FromUserID == q.ToUserID && p.ToUserID == q.FromUserID) {
\t\t\t\t\tpairPrivate = true
\t\t\t\t\tbreak
\t\t\t\t}
\t\t\t}
\t\t\tif pairPrivate {
\t\t\t\tcontinue
\t\t\t}
\t\t}
\t\tif p.Visibility == \"public\" || p.FromUserID == u.ID || p.ToUserID == u.ID {
\t\t\tvisible = append(visible, p)
\t\t}
\t}"""


def main():
    MUT.mkdir(parents=True, exist_ok=True)
    if WT.exists():
        subprocess.run(["git", "worktree", "remove", "-f", str(WT)], cwd=ROOT, check=False)
    run("git", "worktree", "add", str(WT), "1125eee49810", "--detach")

    run("git", "checkout", "--", "stage-1/handlers.go", cwd=WT)
    edit_handlers(ACTIVITY_OLD, ACTIVITY_NEW)
    write_patch("m01_pair_hide_public.patch", "stage-1/handlers.go")

    run("git", "checkout", "--", "stage-1/handlers.go", cwd=WT)
    hf = WT / "stage-1" / "handlers.go"
    t = hf.read_text(encoding="utf-8-sig")
    hf.write_text(
        t.replace("if from.Balance < amount {", "if false && from.Balance < amount {", 1),
        encoding="utf-8",
        newline="\n",
    )
    write_patch("m02_skip_insufficient.patch", "stage-1/handlers.go")

    run("git", "checkout", "--", "stage-1/idempotency.go", cwd=WT)
    edit_idempotency(
        "\trec, ok := s.Idempotency[fullKey]",
        "\tdelete(s.Idempotency, fullKey)\n\trec, ok := s.Idempotency[fullKey]",
    )
    write_patch("m03_idempotency_no_replay.patch", "stage-1/idempotency.go")


if __name__ == "__main__":
    main()
