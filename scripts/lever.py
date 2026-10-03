"""Build, boot, test and mutate a stage the same way the official harness does.

    python scripts/lever.py doctor
    python scripts/lever.py build   --stage 1 [--rev REV]
    python scripts/lever.py boot    --stage 1 [--rev REV]       prints BASE_URL, leaves it running
    python scripts/lever.py stop    [--all]                     your seat's services; --all: every seat's
    python scripts/lever.py checks  --suite official|verifier|breaker|uireviewer|endurance --stage 1 [--isolated] [--rev REV] [--base-url URL]
    python scripts/lever.py regress --stage 2 [--rev REV]       every suite, every stage up to 2
    python scripts/lever.py mutate  --stage 1 --mutant mutants/stage-1/m01.patch [--suites official,verifier,breaker]
    python scripts/lever.py mutate  --stage 1 --catalog         every patch in mutants/stage-1/
    python scripts/lever.py reexec  --evidence E-verifier-3
    python scripts/lever.py pack                                submission check

Services get the published limits: PORT=8080, 2 CPUs, 2 GiB, healthy on /health within 60 s.
--rev builds from a clean export of that commit, so uncommitted files never leak in.
Suites are pytest folders: <suite folder>/stage-N/, given BASE_URL in the environment.
"""
import argparse
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid

from seat import caller_seat

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
STATE = ROOT / ".umbra"
CONFIG = json.loads((HERE / "lever.json").read_text(encoding="utf-8"))
SUITES = {"verifier": "verify", "breaker": "attacks", "uireviewer": "review", "endurance": "soak"}
PORT, CPUS, MEMORY, HEALTH = 8080, "2", "2g", 60


def setting(name):
    return os.environ.get(f"UMBRA_{name.upper()}") or CONFIG[name]


def env():
    return {**os.environ, "PYTHONUTF8": "1"}


def run(args, timeout=1800, cwd=None, extra_env=None, echo=True):
    try:
        result = subprocess.run(args, cwd=cwd or ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout,
                                env={**env(), **(extra_env or {})})
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        code, output = 124, f"{exc.stdout or ''}{exc.stderr or ''}\ntimed out after {timeout}s"
    if echo and output.strip():
        print(output.rstrip())
    return code, output


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def stages_up_to(stage):
    return [str(n) for n in range(1, int(stage) + 1)]


def to_wsl(path):
    path = pathlib.Path(path).resolve()
    drive, rest = path.drive.rstrip(":").lower(), path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{rest}"


# --- sources -----------------------------------------------------------------------

def export(rev, extra=()):
    """A clean copy of the repository at `rev`, without any untracked or uncommitted file."""
    target = pathlib.Path(tempfile.mkdtemp(prefix=f"umbra-{rev[:8]}-"))
    archive = target / "src.tar"
    with archive.open("wb") as handle:
        subprocess.run(["git", "archive", "--format=tar", rev], cwd=ROOT, stdout=handle,
                       check=True)
    with tarfile.open(archive) as tar:
        tar.extractall(target / "repo", filter="data")
    archive.unlink()
    return target / "repo"


def source(stage, rev):
    if rev:
        return export(rev) / f"stage-{stage}"
    return ROOT / f"stage-{stage}"


# --- docker ------------------------------------------------------------------------

def build(context, tag):
    if not (context / "Dockerfile").is_file():
        sys.exit(f"no Dockerfile in {context}")
    code, output = run(["docker", "build", "-q", "-t", tag, str(context)], echo=False)
    if code:
        print(output.rstrip())
        sys.exit(f"build failed for {context}")
    return tag


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def healthy(url, container):
    deadline = time.monotonic() + HEALTH
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=2) as response:
                if response.status == 200 and json.loads(response.read()).get("status") == "ok":
                    return round(HEALTH - (deadline - time.monotonic()), 1)
        except (OSError, ValueError):
            pass
        running = git_free(["docker", "inspect", "-f", "{{.State.Running}}", container])
        if running != "true":
            break
        time.sleep(0.25)
    run(["docker", "logs", "--tail", "60", container])
    return None


def git_free(args):
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def start(image, label):
    name = f"umbra-{label}-{uuid.uuid4().hex[:6]}"
    port = free_port()
    code, output = run(["docker", "run", "-d", "--name", name, "--cpus", CPUS,
                        "--memory", MEMORY, "-e", f"PORT={PORT}",
                        "-p", f"127.0.0.1:{port}:{PORT}", image], echo=False)
    if code:
        sys.exit(f"docker run failed: {output.strip()}")
    url = f"http://127.0.0.1:{port}"
    seconds = healthy(url, name)
    if seconds is None:
        stop_container(name)
        sys.exit(f"service did not become healthy at {url}/health within {HEALTH}s")
    STATE.mkdir(exist_ok=True)
    (STATE / f"{name}.json").write_text(json.dumps({"container": name, "url": url,
                                                    "seat": caller_seat() or "operator"}))
    return name, url, seconds


def stop_container(name):
    run(["docker", "rm", "-f", name], echo=False)
    (STATE / f"{name}.json").unlink(missing_ok=True)


class Service:
    def __init__(self, context, label):
        self.context, self.label = context, label

    def __enter__(self):
        image = build(self.context, f"umbra/{self.label}:{uuid.uuid4().hex[:8]}")
        self.name, self.url, _ = start(image, self.label)
        self.image = image
        return self.url

    def __exit__(self, *exc):
        stop_container(self.name)
        run(["docker", "rmi", "-f", self.image], echo=False)


# --- suites ------------------------------------------------------------------------

def official(stage, context_root, isolated):
    """The organizers' harness on a repository root holding stage-N folders."""
    track, kickoff = setting("track"), pathlib.Path(setting("kickoff"))
    out = STATE / "runs" / uuid.uuid4().hex[:10]
    out.parent.mkdir(parents=True, exist_ok=True)
    if isolated:
        command = (f"cd {to_wsl(kickoff)} && PYTHONUTF8=1 {setting('wsl_python')} -m harness run "
                   f"--track {track} --repo {to_wsl(context_root)} --stage {stage} "
                   f"--mode isolated --out {to_wsl(out)}")
        code, _ = run(["wsl", "-d", setting("wsl_distro"), "--", "bash", "-lc", command],
                      timeout=3600)
    else:
        code, _ = run([setting("python"), "-m", "harness", "run", "--track", track,
                       "--repo", str(context_root), "--stage", stage, "--mode", "host",
                       "--out", str(out)], cwd=kickoff, timeout=3600)
    print(f"official report: {out / 'report.json'}")
    return code


def pytest_suite(suite, stage, url, repo_root):
    folder = SUITES[suite]
    targets = [str(repo_root / folder / f"stage-{n}") for n in stages_up_to(stage)
               if (repo_root / folder / f"stage-{n}").is_dir()]
    if not targets:
        print(f"{suite}: no tests under {folder}/stage-1..{stage}; counts as a failure")
        return 1
    code, _ = run([setting("python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets],
                  extra_env={"BASE_URL": url}, timeout=3600)
    return code


def suite_on(suite, stage, rev, isolated, base_url=None):
    repo_root = export(rev) if rev else ROOT
    if suite == "official":
        return official(stage, repo_root, isolated)
    if base_url:
        return pytest_suite(suite, stage, base_url, repo_root)
    with Service(repo_root / f"stage-{stage}", f"s{stage}-{suite}") as url:
        return pytest_suite(suite, stage, url, repo_root)


# --- commands ----------------------------------------------------------------------

def cmd_doctor(a):
    problems = []
    for label, args in [("git", ["git", "--version"]), ("docker", ["docker", "info", "-f", "{{.ServerVersion}}"]),
                        ("harness python", [setting("python"), "-c", "import pytest, httpx; print('ok')"])]:
        code, output = run(args, timeout=60, echo=False)
        print(f"{'ok  ' if code == 0 else 'FAIL'} {label}: {output.strip().splitlines()[-1] if output.strip() else ''}")
        problems += [label] if code else []
    kickoff = pathlib.Path(setting("kickoff"))
    ok = (kickoff / "harness" / "cli.py").is_file()
    print(f"{'ok  ' if ok else 'FAIL'} kickoff: {kickoff}")
    problems += [] if ok else ["kickoff"]
    code, output = run(["wsl", "-d", setting("wsl_distro"), "--", "bash", "-lc",
                        f"{setting('wsl_python')} -c 'import pytest; print(1)' && docker info -f '{{{{.ServerVersion}}}}'"],
                       timeout=120, echo=False)
    print(f"{'ok  ' if code == 0 else 'FAIL'} isolated mode via WSL: {output.strip().splitlines()[-1] if output.strip() else ''}")
    problems += ["wsl"] if code else []
    print(f"track={setting('track')} code rev={git('log', '-1', '--format=%h', '--', 'stage-*') or 'none'}")
    sys.exit(1 if problems else 0)


def cmd_build(a):
    context = source(a.stage, a.rev)
    tag = build(context, f"umbra/stage-{a.stage}:{(a.rev or 'work')[:12]}")
    print(f"built {tag} from {context}")


def cmd_boot(a):
    context = source(a.stage, a.rev)
    image = build(context, f"umbra/stage-{a.stage}:{(a.rev or 'work')[:12]}")
    name, url, seconds = start(image, f"s{a.stage}")
    print(f"BASE_URL={url}\ncontainer={name} healthy after {seconds}s; stop with: python scripts/lever.py stop")


def cmd_stop(a):
    """Stops only the services your seat booted; other seats may be mid-run on theirs."""
    me = caller_seat() or "operator"
    for path in sorted(STATE.glob("umbra-*.json")) if STATE.is_dir() else []:
        state = json.loads(path.read_text())
        if a.all or state.get("seat", "operator") == me:
            stop_container(state["container"])
            print(f"stopped {path.stem}")


def cmd_checks(a):
    code = suite_on(a.suite, a.stage, a.rev, a.isolated, a.base_url)
    print(f"{a.suite} stage {a.stage}: {'PASS' if code == 0 else 'FAIL'} (exit {code})")
    sys.exit(code)


def cmd_regress(a):
    repo_root = export(a.rev) if a.rev else ROOT
    results = {"official": official(a.stage, repo_root, isolated=False)}
    with Service(repo_root / f"stage-{a.stage}", f"s{a.stage}-regress") as url:
        for suite, folder in SUITES.items():
            if any((repo_root / folder / f"stage-{n}").is_dir() for n in stages_up_to(a.stage)):
                results[suite] = pytest_suite(suite, a.stage, url, repo_root)
    for suite, code in results.items():
        print(f"{suite:<10} {'PASS' if code == 0 else 'FAIL'}")
    sys.exit(0 if not any(results.values()) else 1)


def apply_patch(repo_root, patch):
    code, output = run(["git", "apply", "--unidiff-zero", str(patch.resolve())],
                       cwd=repo_root, echo=False)
    if code:
        code, output = run(["git", "apply", "-p1", "--reject", str(patch.resolve())],
                           cwd=repo_root, echo=False)
    return code == 0, output


def mutate_one(stage, patch, suites, rev):
    repo_root = export(rev or git("rev-parse", "HEAD"))
    applied, output = apply_patch(repo_root, patch)
    if not applied:
        return "invalid", output.strip()[:200]
    killed_by = []
    for suite in suites:
        if suite == "official":
            code = official(stage, repo_root, isolated=False)
        else:
            with Service(repo_root / f"stage-{stage}", f"s{stage}-mut") as url:
                code = pytest_suite(suite, stage, url, repo_root)
        if code:
            killed_by.append(suite)
    shutil.rmtree(repo_root.parent, ignore_errors=True)
    return ("killed" if killed_by else "SURVIVED"), ",".join(killed_by)


def cmd_mutate(a):
    suites = [s.strip() for s in a.suites.split(",") if s.strip()]
    patches = (sorted((ROOT / "mutants" / f"stage-{a.stage}").glob("*.patch")) if a.catalog
               else [ROOT / a.mutant])
    if not patches:
        sys.exit(f"no mutants under mutants/stage-{a.stage}/")
    rows = []
    for patch in patches:
        verdict, detail = mutate_one(a.stage, patch, suites, a.rev)
        rows.append((patch.name, verdict, detail))
        print(f"MUTANT {patch.name}: {verdict} {detail}")
    killed = sum(1 for _, verdict, _ in rows if verdict == "killed")
    valid = sum(1 for _, verdict, _ in rows if verdict != "invalid")
    print(f"mutation score {killed}/{valid} (invalid {len(rows) - valid})")
    sys.exit(0 if valid and killed == valid else 1)


def cmd_reexec(a):
    rows = []
    for path in sorted((ROOT / "record").glob("*.jsonl")):
        rows += [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    row = next((r for r in rows if r.get("id") == a.evidence and r["type"] == "evidence"), None)
    if not row:
        sys.exit(f"no evidence {a.evidence}")
    shell = ["cmd", "/c", row["run"]] if os.name == "nt" else ["sh", "-c", row["run"]]
    code, _ = run(shell, timeout=3600)
    same = (code == 0) == (row["exit"] == 0)
    print(f"{a.evidence}: recorded exit {row['exit']}, re-executed exit {code} -> {'REPRODUCED' if same else 'DIVERGED'}")
    sys.exit(0 if same else 1)


def cmd_pack(a):
    kickoff = pathlib.Path(setting("kickoff"))
    code, _ = run([setting("python"), "-m", "harness", "check", "--track", setting("track"),
                   str(ROOT)], cwd=kickoff, timeout=600)
    sys.exit(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(__doc__.splitlines()[2:]))
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, handler):
        p = sub.add_parser(name)
        p.set_defaults(handler=handler)
        return p

    add("doctor", cmd_doctor)
    for name, handler in [("build", cmd_build), ("boot", cmd_boot)]:
        p = add(name, handler)
        p.add_argument("--stage", required=True)
        p.add_argument("--rev")
    p = add("stop", cmd_stop)
    p.add_argument("--all", action="store_true")
    p = add("checks", cmd_checks)
    p.add_argument("--suite", required=True, choices=["official", *SUITES])
    p.add_argument("--stage", required=True)
    p.add_argument("--isolated", action="store_true")
    p.add_argument("--rev")
    p.add_argument("--base-url")
    p = add("regress", cmd_regress)
    p.add_argument("--stage", required=True)
    p.add_argument("--rev")
    p = add("mutate", cmd_mutate)
    p.add_argument("--stage", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--mutant")
    group.add_argument("--catalog", action="store_true")
    p.add_argument("--suites", default="official,verifier,breaker")
    p.add_argument("--rev")
    p = add("reexec", cmd_reexec)
    p.add_argument("--evidence", required=True)
    add("pack", cmd_pack)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
