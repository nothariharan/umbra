"""Seed stage 4 requirements. Run from repo root."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

REQS = [
    ("S4-R1", "Intro", "Stages 1–3 requirements continue; ten idempotent write paths (stage-1 five, stage-2 authorizations/captures, stage-3 corrections, stage-4 refunds and correction batches)."),
    ("S4-R2", "Refunds", "POST /payments/{payment_id}/refunds requires idempotency key; body amount required."),
    ("S4-R3", "Refunds", "Only original receiver may refund; else 403 forbidden; unknown payment 404."),
    ("S4-R4", "Refunds", "Target may be direct, request, or capture payment, never a refund; refund-of-refund 422 invalid_refund_target."),
    ("S4-R5", "Refunds", "Invalid amount 422 validation_failed."),
    ("S4-R6", "Refunds", "Cumulative refunds must not exceed payment corrected amount; 422 refund_exceeds_payment."),
    ("S4-R7", "Refunds", "Refund is new opposite-direction payment with refund_of, request_id and authorization_id null, original note and visibility."),
    ("S4-R8", "Refunds", "Success 201 with payment body; idempotent replay 200 with original body."),
    ("S4-R9", "Refunds", "Debit receiver available funds atomically; 409 insufficient_funds on failure."),
    ("S4-R10", "Refunds", "Refunds never reopen request/authorization or restore released hold; non-refund payments have refund_of null."),
    ("S4-R11", "Corrections", "Stage-3 single corrections remain for ordinary direct/request; capture and refund payments immutable 422 linked_payment_immutable."),
    ("S4-R12", "Corrections", "Correction cannot reduce below already-refunded amount 422 refund_exceeds_payment; debits checked against available."),
    ("S4-R13", "Batch auth", "POST /correction-batches requires settlement operator and idempotency; 401/403 same as settlements."),
    ("S4-R14", "Batch body", "corrections array 1..32 items with distinct payment_ids else 422 validation_failed."),
    ("S4-R15", "Batch items", "Each item ordinary correction fields; unknown payment 404; stale expected_revision 409."),
    ("S4-R16", "Batch scope", "Operator may correct ordinary, request, settlement payments; captures and refunds remain immutable."),
    ("S4-R17", "Settlements", "Correcting any settlement member requires every member of that settlement else 422 incomplete_settlement."),
    ("S4-R18", "Settlements", "Members of one settlement must share identical effective instants (offset spellings may differ) else 422 validation_failed."),
    ("S4-R19", "Batch misc", "Single-payment corrections remain for nonmembers; unknown JSON fields ignored on batch."),
    ("S4-R20", "Batch errors", "Precedence: per-item errors in input order, settlement completeness, resulting current available, then historical total/available at every effective/event boundary with existing codes."),
    ("S4-R21", "Batch atomicity", "Rejected batch leaves history, balances, and idempotency records unchanged."),
    ("S4-R22", "Batch success", "201 with correction_batch_id, recorded_at, revisions in input order; shared recorded_at strictly after every member prior recorded_at; each revision exposes correction_batch_id."),
    ("S4-R23", "Batch replay", "Effective times not later than now; original payments/receipts unchanged; payment/settlement retries original bodies; statements reflect new revisions; snapshot tokens frozen; batch replay 200 original response."),
    ("S4-R24", "Settlements", "Settlement member may be refunded under refund rules; refunds never change settlement membership."),
    ("S4-R25", "Concurrency", "Concurrent corrections sharing any expected payment revision cannot both succeed."),
    ("S4-R26", "Import", "Stage-4 service accepts same-team stages 1–3 exports retaining settlement membership, corrections, and snapshots."),
    ("S4-R27", "Delivery", "stage-4/ copies sealed stage-3 baseline; Dockerfile and RUN.md; all earlier stage checks still pass."),
    ("S4-R28", "UI regression", "Stage 1–3 UI testids and flows remain on stage-4 build at narrow and desktop widths."),
]

RULINGS = [
    ("S4-U1", "S4-R27", "Builder copies sealed stage-3 folder from rev 55207f5fd143 into stage-4/ before implementing deltas."),
    ("S4-U2", "S4-R1", "Stage 4 specification text is the human dispatch verbatim block in room 2fd5fd46-b6dc-4ce5-95bd-bbb53029fa2a (2026-10-04 stage-4 dispatch)."),
]


def main():
    for rid, src, text in REQS:
        subprocess.check_call(
            [PY, "scripts/record.py", "requirement", "--seat", "lead", "--id", rid,
             "--stage", "4", "--source", src, "--text", text],
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
