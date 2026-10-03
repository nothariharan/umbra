"""Register S2-UI-C* checks for UIReviewer stage 2 part 1/2."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / "scripts" / "record.py"

CHECKS = [
    (
        "S2-UI-C1",
        "S2-R2",
        "Playwright: required routes / /requests /split /signup /login /authorizations at 375px and 1280px",
    ),
    (
        "S2-UI-C2",
        "S2-R4",
        "Playwright: mandated data-testid on home and core forms",
    ),
    (
        "S2-UI-C3",
        "S2-R5",
        "Playwright: no horizontal scroll on required routes at 375px and 1280px; screenshots",
    ),
    (
        "S2-UI-C4",
        "S2-R6",
        "Playwright: signup/login testids, auth-error, signed-in chrome on every screen",
    ),
    (
        "S2-UI-C5",
        "S2-R7",
        "Playwright: wallet-balance data-amount and formatted text; pay-visibility; pay-error validation",
    ),
    (
        "S2-UI-C6",
        "S2-R10",
        "Playwright: activity-list, activity-item-*, parties, amount, note, empty-activity",
    ),
    (
        "S2-UI-C7",
        "S2-R11",
        "Playwright: incoming/outgoing lists, request-item-*, pending-only actions, empty-requests",
    ),
    (
        "S2-UI-C8",
        "S2-R12",
        "Playwright: split-* testids; split-preview shares match equal-split rule before POST",
    ),
    (
        "S2-UI-C9",
        "S2-R28",
        "Playwright: /authorizations wallet-available headline, wallet-held when nonzero, authorize form",
    ),
    (
        "S2-UI-C10",
        "S2-R29",
        "Playwright: capture/void controls on permitted open auths; authorization-error path reserved",
    ),
]


def main() -> int:
    for cid, reqs, text in CHECKS:
        subprocess.run(
            [
                sys.executable,
                str(PY),
                "check",
                "--seat",
                "uireviewer",
                "--id",
                cid,
                "--req",
                reqs,
                "--text",
                text,
            ],
            cwd=ROOT,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
