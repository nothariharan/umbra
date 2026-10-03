"""Register S2-C* checks in record/verifier.jsonl (Lead REQUEST stage 2)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / "scripts" / "record.py"

CHECKS = [
    ("S2-C1", "S2-R31", "stage-2 delivery artifacts extend sealed stage-1"),
    ("S2-C2", "S2-R2", "required routes reachable by URL"),
    ("S2-C3", "S2-R3", "/requests and /authorizations HTML vs JSON negotiation"),
    ("S2-C4", "S2-R4,S2-R5", "mandated data-testid on core screens; 375px smoke"),
    ("S2-C5", "S2-R6", "signup/login auth UI testids"),
    ("S2-C6", "S2-R7,S2-R8", "pay form formatting, idempotent resubmit without field change"),
    ("S2-C7", "S2-R9", "request form testids and request-error"),
    ("S2-C8", "S2-R10", "activity feed testids and visibility attrs"),
    ("S2-C9", "S2-R11", "requests screen lists and pending actions"),
    ("S2-C10", "S2-R12", "split preview shares match server before POST"),
    ("S2-C11", "S2-R13", "post-action refresh without manual reload"),
    ("S2-C12", "S2-R14", "wallet-refresh latest-wins ordering"),
    ("S2-C13", "S2-R15", "competing clients pay-error and pay-uncertain"),
    ("S2-C14", "S2-R16", "stage-1 export/import upgrade preserves session and retries"),
    ("S2-C15", "S2-R17", "total conservation with holds and captures"),
    ("S2-C16", "S2-R20", "GET /me total, available, held fields"),
    ("S2-C17", "S2-R18,S2-R21", "available funds gate; POST /authorizations idempotent hold"),
    ("S2-C18", "S2-R19,S2-R22", "capture idempotency and payment shape"),
    ("S2-C19", "S2-R23", "capture/void error codes per spec table"),
    ("S2-C20", "S2-R24", "POST void payer-only idempotent"),
    ("S2-C21", "S2-R25", "GET /authorizations filters and party scope"),
    ("S2-C22", "S2-R26", "authorization_ttl_seconds default and validation"),
    ("S2-C23", "S2-R27", "expiry releases holds on read"),
    ("S2-C24", "S2-R28", "authorizations UI wallet-available headline testids"),
    ("S2-C25", "S2-R29", "capture/void controls and authorization-error"),
    ("S2-C26", "S2-R1", "stage-1 API regression via bundled official+verifier stage 1 at SUBMIT"),
    ("S2-C27", "S2-R30", "concurrent API correctness and invariants"),
    ("S2-C32", "S2-R1,S2-R2,S2-R3,S2-R4,S2-R5,S2-R6,S2-R7,S2-R8,S2-R9,S2-R10,S2-R11,S2-R12,S2-R13,S2-R14,S2-R15,S2-R16,S2-R17,S2-R18,S2-R19,S2-R20,S2-R21,S2-R22,S2-R23,S2-R24,S2-R25,S2-R26,S2-R27,S2-R28,S2-R29,S2-R30,S2-R31", "official harness stage 2 isolated on SUBMIT"),
]


def main() -> int:
    for cid, reqs, text in CHECKS:
        cmd = [
            sys.executable,
            str(PY),
            "check",
            "--seat",
            "verifier",
            "--id",
            cid,
            "--req",
            reqs,
            "--text",
            text,
        ]
        subprocess.run(cmd, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
