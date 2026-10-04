"""Send Lead's final report to the human who dispatched the run.

    python scripts/report.py --seat lead --room ROOM --file evidence/lead/report.md
"""
import argparse
import json
import pathlib
import re
import sys

from handoff import SPEC_MARK, band
from record import entries
from seat import refuse_unless

LAST_STAGE = re.compile(r"stop after stage (\d+)|^Run stage (\d+) of .*then stop", re.MULTILINE)


def dispatch(room):
    """The newest human dispatch: (sender id, text)."""
    for page in range(1, 50):
        result = json.loads(band("room", "messages", room, "--type", "text", "--json",
                                 "--page", str(page)) or "{}")
        rows = sorted(result.get("messages") or [], key=lambda r: r["inserted_at"], reverse=True)
        for row in rows:
            if row.get("sender_type") != "Agent" and SPEC_MARK.search(row.get("content") or ""):
                return row["sender_id"], row["content"]
        if not result.get("has_more"):
            break
    sys.exit(f"no human dispatch found in room {room}")


def unsealed(text):
    """The first dispatched stage without a SEAL in the record, or None."""
    last = max((int(n) for m in LAST_STAGE.finditer(text) for n in m.groups() if n), default=None)
    if last is None:
        return None
    sealed = {str(r.get("stage")) for r in entries()
              if r.get("type") == "verdict" and r.get("kind") == "SEAL"}
    return next((n for n in range(1, last + 1) if str(n) not in sealed), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seat", required=True)
    parser.add_argument("--room", required=True)
    parser.add_argument("--file", required=True, help="the report, as markdown")
    args = parser.parse_args()
    if args.seat.lower() != "lead":
        sys.exit("only Lead sends the final report")
    refuse_unless("lead", "report")
    body = pathlib.Path(args.file).read_text(encoding="utf-8").strip()
    human, text = dispatch(args.room)
    stage = unsealed(text)
    if stage is not None and "blocker" not in body.lower():
        sys.exit(f"refused: the dispatch runs through a stage that is not sealed yet. Open stage "
                 f"{stage} now: its specification is in the dispatch, and "
                 f"`python scripts/handoff.py --stage {stage}` sends it. A report before the last "
                 "stage is sealed must name the blocker that ends the run.")
    handle = next((m.group(1) for m in re.finditer(r"^(\S+) \[.*?id=([0-9a-f-]{36})",
                                                    band("room", "participants", args.room),
                                                    re.MULTILINE) if m.group(2) == human), None)
    if not handle:
        sys.exit(f"the dispatcher {human} is not a participant of room {args.room}")
    band("--session", "umbra-lead", "send", args.room, f"@{handle} {body}\n")
    print(f"final report sent ({len(body)} characters)")


if __name__ == "__main__":
    main()
