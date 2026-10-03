"""Send one protocol message to named seats in the room.

    python scripts/send.py --seat builder --to verifier,breaker --body "SUBMIT stage=1 ..."
    python scripts/send.py --seat verifier --to builder,certifier --body-file evidence/verifier/accept.md

A turn's closing text reaches only the seat that woke you; this reaches the seats you name.
--room is needed only when your seat belongs to more than one room.
"""
import argparse
import pathlib
import re
import sys

from handoff import band
from seat import refuse_unless

ROOM_ID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def room_of(seat, room):
    if room:
        return room
    rooms = re.findall(rf"^({ROOM_ID})\b", band("--session", f"umbra-{seat}", "chat", "list"),
                       re.MULTILINE)
    if len(rooms) != 1:
        sys.exit(f"your seat is in {len(rooms)} rooms; pass --room with the room from the dispatch")
    return rooms[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="\n".join(__doc__.splitlines()[1:]))
    parser.add_argument("--seat", required=True)
    parser.add_argument("--to", required=True, help="comma-separated seat names")
    parser.add_argument("--room")
    body = parser.add_mutually_exclusive_group(required=True)
    body.add_argument("--body")
    body.add_argument("--body-file")
    args = parser.parse_args()
    seat = args.seat.lower()
    refuse_unless(seat, "send")
    room = room_of(seat, args.room)
    listing = band("room", "participants", room)
    ids = {m.group(2): m.group(1)
           for m in re.finditer(r"^(\S+/(\w+)) \[", listing, re.MULTILINE)}
    names = [n.strip().lower() for n in args.to.split(",") if n.strip()]
    missing = [n for n in names if n not in ids]
    if missing:
        sys.exit(f"not in room {room}: {', '.join(missing)}; present: {', '.join(sorted(ids))}")
    if seat in names:
        sys.exit("you cannot address yourself")
    text = args.body if args.body is not None else \
        pathlib.Path(args.body_file).read_text(encoding="utf-8")
    mentions = " ".join(f"@{ids[n]}" for n in names)
    band("--session", f"umbra-{seat}", "send", room, f"{mentions} {text.strip()}\n")
    print(f"sent to {', '.join(names)} in {room}")


if __name__ == "__main__":
    main()
