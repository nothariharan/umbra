"""Send Lead's final report to the human who dispatched the run.

    python scripts/report.py --seat lead --room ROOM --file evidence/lead/report.md
"""
import argparse
import json
import pathlib
import re
import sys

from handoff import SPEC_MARK, band
from seat import refuse_unless


def dispatcher(room):
    for page in range(1, 50):
        result = json.loads(band("room", "messages", room, "--type", "text", "--json",
                                 "--page", str(page)) or "{}")
        for row in result.get("messages") or []:
            if row.get("sender_type") != "Agent" and SPEC_MARK.search(row.get("content") or ""):
                return row["sender_id"]
        if not result.get("has_more"):
            break
    sys.exit(f"no human dispatch found in room {room}")


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
    human = dispatcher(args.room)
    handle = next((m.group(1) for m in re.finditer(r"^(\S+) \[.*?id=([0-9a-f-]{36})",
                                                    band("room", "participants", args.room),
                                                    re.MULTILINE) if m.group(2) == human), None)
    if not handle:
        sys.exit(f"the dispatcher {human} is not a participant of room {args.room}")
    band("--session", "umbra-lead", "send", args.room, f"@{handle} {body}\n")
    print(f"final report sent ({len(body)} characters)")


if __name__ == "__main__":
    main()
