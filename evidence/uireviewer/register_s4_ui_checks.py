"""Register S4-UI-C* checks for UIReviewer stage 4 (S4-R28 gate)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / "scripts" / "record.py"

CHECKS = [
    (
        "S4-UI-C1",
        "S4-R28",
        "Playwright stage-4 build: routes / /requests /split /signup /login /authorizations at 375+1280",
    ),
    (
        "S4-UI-C2",
        "S4-R28",
        "Playwright: mandated data-testid on home and core forms",
    ),
    (
        "S4-UI-C3",
        "S4-R28",
        "Playwright: no horizontal scroll on required routes; screenshots",
    ),
    (
        "S4-UI-C4",
        "S4-R28",
        "Playwright: signup/login testids, auth-error, signed-in chrome",
    ),
    (
        "S4-UI-C5",
        "S4-R28",
        "Playwright: wallet-balance, pay-visibility, pay-error validation",
    ),
    (
        "S4-UI-C6",
        "S4-R28",
        "Playwright: activity-list and activity-item fields, empty-activity",
    ),
    (
        "S4-UI-C7",
        "S4-R28",
        "Playwright: incoming/outgoing requests, pending actions, empty-requests",
    ),
    (
        "S4-UI-C8",
        "S4-R28",
        "Playwright: split-* testids and split-preview equal-split rule",
    ),
    (
        "S4-UI-C9",
        "S4-R28",
        "Playwright: /authorizations wallet-available/held and authorize form",
    ),
    (
        "S4-UI-C10",
        "S4-R28",
        "Playwright: capture/void on permitted open auths; authorization-error path",
    ),
    (
        "S4-UI-C11",
        "S4-R28",
        "Playwright: authorization-amount/expires; authorize-error insufficient",
    ),
    (
        "S4-UI-C12",
        "S4-R28",
        "Playwright: wallet-held absent at zero; empty-authorizations",
    ),
    (
        "S4-UI-C13",
        "S4-R28",
        "Playwright: unchanged pay form resubmit must not debit twice",
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
