"""Seed stage 3 requirements. Run from repo root."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

REQS = [
    ("S3-R1", "Intro", "Stages 1–2 requirements continue; stage 3 adds statements, corrections, temporal reads, snapshots."),
    ("S3-R2", "Payment timestamps", "Every payment includes RFC3339 created_at with offset on all returning endpoints."),
    ("S3-R3", "Activity order", "GET /activity orders by created_at as before."),
    ("S3-R4", "Seeded created_at", "Seeded payments may set created_at; omission uses reset time; future created_at on reset yields 422 validation_failed with no state change."),
    ("S3-R5", "Seeded balance", "Fixture balance remains after all seeded payments; loading seeded payments must not change balances."),
    ("S3-R6", "GET /me as_of", "Optional as_of RFC3339 with offset; invalid temporal input 422 validation_failed."),
    ("S3-R7", "as_of balance", "Balance at as_of includes payments with created_at at or before as_of; edges for latest/earliest/opening."),
    ("S3-R8", "as_of echo", "Response echoes as_of exactly when supplied."),
    ("S3-R9", "GET /statement params", "from/to/limit/offset with defaults; half-open [from,to)."),
    ("S3-R10", "Statement entries", "Oldest-first by created_at then id; payment, delta, balance_after per entry."),
    ("S3-R11", "Statement balances", "opening_balance before from; closing_balance before to; opening plus deltas equals closing in full window."),
    ("S3-R12", "Statement pagination", "limit/offset must not change balance_after or window opening/closing balances."),
    ("S3-R13", "Statement visibility", "Only caller sent/received payments; activity feed visibility rules do not apply."),
    ("S3-R14", "Revision model", "Revision 1 amount original; effective_at=recorded_at=created_at; seeded times consistent."),
    ("S3-R15", "Opening balances", "Opening balances from seeds minus original payment net; corrections must not change seeded opening balances."),
    ("S3-R16", "POST corrections", "Sender-only idempotent correction with full body validation and error codes per spec."),
    ("S3-R17", "Correction effects", "Atomic wallet delta same parties; insufficient_funds and historical_overdraft preserve state on failure."),
    ("S3-R18", "Correction concurrency", "stale_revision, idempotency replay 200, idempotency_key_reuse 409; recorded_at strictly increases."),
    ("S3-R19", "Activity and revisions read", "Activity shows original payment only; GET revisions party-only ordered; third party 404."),
    ("S3-R20", "known_at selection", "Optional known_at on GET /me and GET /statement; revision selection at or before known_at; echo known_at."),
    ("S3-R21", "Corrected statement", "Order by effective_at then id; entry includes revision times; zero-amount revisions; payment.amount is selected amount."),
    ("S3-R22", "Snapshot token", "First statement returns snapshot; paging via snapshot only limit/offset; invalid combo 422; bad token 404."),
    ("S3-R23", "Snapshot stability", "Snapshots frozen through concurrent writes; concurrent same expected_revision cannot both succeed."),
    ("S3-R24", "Settlements import", "Settlement member single correction immutable; import stage-1/2 exports with auth ledger."),
    ("S3-R25", "Capture immutable", "Capture correction returns linked_payment_immutable."),
    ("S3-R26", "Historical holds me", "GET /me with as_of and known_at: total/available/held consistent with hold lifecycle and event times."),
    ("S3-R27", "closed_at", "Authorizations expose closed_at; historical_overdraft vs insufficient_funds precedence on corrections."),
    ("S3-R28", "Statement vs holds", "Statement lists payments only; captures once with links; snapshots unchanged after lifecycle/correction."),
    ("S3-R29", "Delivery", "stage-3/ copies sealed stage-2 baseline; Dockerfile and RUN.md; earlier stage checks still pass."),
    ("S3-R30", "UI regression", "Stage 1–2 UI testids and flows remain on stage 3 build at narrow and desktop widths."),
]

RULINGS = [
    ("S3-U1", "S3-R29", "Builder copies sealed stage-2 folder from rev b013f5e17143 into stage-3/ before implementing deltas."),
    ("S3-U2", "S3-R1", "Stage 3 specification text is the human dispatch verbatim block in room 2fd5fd46-b6dc-4ce5-95bd-bbb53029fa2a (2026-10-04)."),
]


def main():
    for rid, src, text in REQS:
        subprocess.check_call(
            [PY, "scripts/record.py", "requirement", "--seat", "lead", "--id", rid,
             "--stage", "3", "--source", src, "--text", text],
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
