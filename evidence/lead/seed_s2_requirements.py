"""Seed stage 2 requirements. Run from repo root."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

REQS = [
    ("S2-R1", "§ intro", "Stage 1 requirements continue; stage 2 adds browser UI and payment authorizations with captures."),
    ("S2-R2", "Routes", "Required routes: /, /requests, /split, /signup, /login, /authorizations; reachable by URL where listed."),
    ("S2-R3", "Content negotiation", "/requests and /authorizations serve HTML for Accept text/html and JSON otherwise."),
    ("S2-R4", "data-testid", "UI exposes all mandated data-testid attributes for integration testing."),
    ("S2-R5", "Product quality", "Coherent consumer finance UI; available funds headline when holds exist; usable at 375px and desktop without horizontal scroll."),
    ("S2-R6", "Auth UI", "Signup/login testids; auth-error; current-user, current-handle, logout-button when signed in."),
    ("S2-R7", "Balance pay /", "wallet-balance with data-amount; pay form decimal input; pay-visibility; pay-error; formatted amount rules per minor_units."),
    ("S2-R8", "Pay form idempotency UI", "Unchanged pay form resubmit without field change must not double-pay; changing field allows new payment."),
    ("S2-R9", "Request form /", "request-* testids and request-error on refusal."),
    ("S2-R10", "Activity /", "activity-list, activity-item-*, parties, amount, note, empty-activity; feed contract unchanged."),
    ("S2-R11", "Requests screen", "incoming/outgoing lists, request-item-*, actions only on pending, empty-requests."),
    ("S2-R12", "Split screen", "split-* testids; split-preview matches server shares before POST; split-error on refusal."),
    ("S2-R13", "Post-action refresh", "After successful write, same-page balance/feed/requests update without manual reload."),
    ("S2-R14", "wallet-refresh", "Latest refresh wins; stale responses must not overwrite newer balance/feed."),
    ("S2-R15", "Competing clients UI", "Insufficient funds shows pay-error and refreshes; stale pay button removed after remote cancel; pay-uncertain on lost response with same idempotency retry."),
    ("S2-R16", "Stage-1 upgrade", "Import stage-1 export keeps session; pending requests payable; lost payment retry survives import."),
    ("S2-R17", "Invariant total", "Sum of wallet total equals seeded total after reset; holds move no money until capture."),
    ("S2-R18", "Invariant available", "available = total − held never negative; spends checked against available."),
    ("S2-R19", "Invariant capture", "Cumulative captures ≤ authorized amount; each idempotent capture moves money once."),
    ("S2-R20", "GET /me fields", "balance equals total; available and held exposed; no holds means balance=available, held=0."),
    ("S2-R21", "POST /authorizations", "Idempotent hold; insufficient on available; self_payment; not in activity feed."),
    ("S2-R22", "POST capture", "Idempotent; receiver only; payment shape with authorization_id; final default releases remainder; final false extended mode."),
    ("S2-R23", "Capture errors", "authorization_not_open, authorization_expired, capture_exceeds_authorization, forbidden, not_found per spec table."),
    ("S2-R24", "POST void", "Payer only; 200 idempotent void; authorization_not_open when captured/expired."),
    ("S2-R25", "GET /authorizations", "Caller payer or receiver only; direction/status filters; expired clock status."),
    ("S2-R26", "Fixture auth TTL", "authorization_ttl_seconds default 600; seeded holds validation; available derived."),
    ("S2-R27", "Expiry", "Authorization expired at or before now holds nothing; reads reflect expiry without wall-clock request."),
    ("S2-R28", "Auth UI /authorizations", "wallet-available headline; wallet-held when nonzero; authorize form; authorization list testids."),
    ("S2-R29", "Auth actions UI", "capture/void controls only on permitted open auths; authorization-error; empty-authorizations."),
    ("S2-R30", "Concurrent correctness", "Concurrent API requests equivalent to some serial order; invariants hold at every read."),
    ("S2-R31", "Delivery", "stage-2/ extends stage-1 service with Dockerfile and RUN.md; copy sealed stage-1 baseline first."),
]

RULINGS = [
    ("S2-U1", "S2-R31", "Builder copies sealed stage-1 folder from rev 1125eee49810 into stage-2/ before implementing deltas."),
    ("S2-U2", "S2-R1", "Stage 2 specification text for band handoff is pocketful/spec/stage-2.md in harness kickoff when room dispatch lacks stage 2 verbatim block."),
]


def main():
    for rid, src, text in REQS:
        subprocess.check_call(
            [PY, "scripts/record.py", "requirement", "--seat", "lead", "--id", rid,
             "--stage", "2", "--source", src, "--text", text],
            cwd=ROOT,
        )
    for uid, req, text in RULINGS:
        subprocess.check_call(
            [PY, "scripts/record.py", "ruling", "--seat", "lead", "--id", uid,
             "--req", req, "--text", text],
            cwd=ROOT,
        )
    print("seeded", len(REQS), "requirements")


if __name__ == "__main__":
    main()
