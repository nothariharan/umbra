"""Commit only the paths this seat owns, under the seat's name.

    python scripts/commit.py --seat builder -m "S1-R3 S1-R4: reject malformed input"

Other seats' changes in the shared checkout are left alone. Retries while another seat
holds the index lock.
"""
import argparse
import fnmatch
import json
import pathlib
import subprocess
import sys
import time

from seat import refuse_unless

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SEATS = HERE / "seats.json"


def git(*args, check=True):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8")
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result


def locked(error):
    return "index.lock" in str(error)


def with_retry(*args):
    for attempt in range(40):
        try:
            return git(*args)
        except RuntimeError as error:
            if not locked(error) or attempt == 39:
                raise
            time.sleep(0.5)


def owns(patterns, path):
    for pattern in patterns:
        if pattern.endswith("/"):
            head = path.split("/", 1)[0] + "/"
            if fnmatch.fnmatch(head, pattern) or path.startswith(pattern):
                return True
        elif fnmatch.fnmatch(path, pattern):
            return True
    return False


def changed():
    out = git("status", "--porcelain", "-z", "--untracked-files=all").stdout
    entries, paths = out.split("\0"), []
    skip = False
    for entry in entries:
        if skip:
            skip = False
            continue
        if not entry:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            skip = True
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seat", required=True)
    parser.add_argument("-m", "--message", required=True)
    args = parser.parse_args()

    seats = {s["name"]: s for s in json.loads(SEATS.read_text(encoding="utf-8"))["seats"]}
    refuse_unless(args.seat.lower(), "commit")
    seat = seats.get(args.seat.lower())
    if not seat:
        sys.exit(f"unknown seat {args.seat}; seats are {', '.join(seats)}")
    mine = [p for p in changed() if owns(seat["owns"], p)]
    others = [p for p in changed() if not owns(seat["owns"], p)]
    if others:
        print(f"left alone, owned by other seats: {', '.join(others[:8])}"
              f"{' ...' if len(others) > 8 else ''}")
    if not mine:
        print(f"nothing to commit for {seat['name']}")
        return
    with_retry("add", "-A", "--", *mine)
    with_retry("-c", f"user.name={seat['title']}",
               "-c", f"user.email={seat['name']}@umbra.invalid",
               "commit", "--no-verify", "-q", "-m", args.message, "--", *mine)
    revision = git("rev-parse", "--short=12", "HEAD").stdout.strip()
    print(f"rev={revision} files={len(mine)}")


if __name__ == "__main__":
    main()
