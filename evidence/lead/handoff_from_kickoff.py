"""Handoff when room lacks Stage N dispatch — reads pocketful/spec/stage-N.md from kickoff."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import handoff  # noqa: E402

KICKOFF = json.loads((ROOT / "scripts" / "lever.json").read_text())["kickoff"]


def spec_text(stage: int) -> str:
    path = pathlib.Path(KICKOFF) / "pocketful" / "spec" / f"stage-{stage}.md"
    if not path.is_file():
        sys.exit(f"missing kickoff spec {path}")
    return path.read_text(encoding="utf-8").strip()


def send_stage(room: str, to: str, stage: int, due: int, note: str, req: str = ""):
    wanted = [r.strip() for r in req.split(",") if r.strip()]
    reqs = handoff.requirements(stage, wanted)
    body = "\n\n".join([
        f"Result repository (absolute path): {ROOT}",
        f"Stage folder: stage-{stage}/",
        note.strip(),
        f"## Requirements\n\n{reqs}",
        f"## Contracts\n\n{handoff.contracts()}",
        f"## Stage {stage} specification, complete and verbatim\n\n{spec_text(stage)}",
    ])
    req_ids = ",".join(wanted) if wanted else "all"
    parts = handoff.split(body)
    mention = f"@{handoff.participant_handle(room, to)}"
    for number, part in enumerate(parts, 1):
        label = "final part" if number == len(parts) else "more parts follow"
        text = (f"{mention} REQUEST stage={stage} req={req_ids} due={due} "
                f"part={number}/{len(parts)}\n{label.capitalize()}.\n\n{part.strip()}\n")
        handoff.band("--session", "umbra-lead", "send", room, text)
        print(f"sent part {number}/{len(parts)} to {to}")


if __name__ == "__main__":
    room = "2fd5fd46-b6dc-4ce5-95bd-bbb53029fa2a"
    send_stage(room, "builder", 2, 45,
               "Copy sealed stage-1 from rev 1125eee49810 into stage-2/, then implement stage 2 UI + authorizations API. Exit: SUBMIT when official stage 2 isolated passes.")
    send_stage(room, "verifier", 2, 30,
               "Write stage 2 checks and reference model for all S2-R*. Exit: suite ready for SUBMIT.")
    send_stage(room, "breaker", 2, 30,
               "Write stage 2 attacks (holds, capture concurrency, UI race). Exit: suite ready for SUBMIT.")
    send_stage(room, "uireviewer", 2, 30,
               "Browser review all stage 2 screens and testids at narrow/wide widths. Exit: suite ready for SUBMIT.",
               req="S2-R2,S2-R4,S2-R5,S2-R6,S2-R7,S2-R10,S2-R11,S2-R12,S2-R28,S2-R29")
