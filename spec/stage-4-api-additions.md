# Pocketful Stage 4 — refunds and batch corrections (extends stage 3)

Stage 1–3 API, UI, invariants, statements, corrections, and temporal reads continue unless amended below.

## Refunds

- `POST /payments/{payment_id}/refunds` — idempotent write; body `{"amount": <minor units>}`; idempotency key required.
- **403** `forbidden` if caller is not the payment’s original receiver; **404** if payment unknown.
- Valid targets: direct, request, or capture payments only; not refund payments (**422** `invalid_refund_target` for refund-of-refund).
- **422** `validation_failed` for invalid amount.
- **422** `refund_exceeds_payment` when cumulative refunds would exceed the payment’s current corrected amount.
- Creates a new payment: opposite direction, `refund_of` = target id, `request_id: null`, `authorization_id: null`, same note/visibility as target; other payments keep `refund_of: null`.
- **201** + payment on first success; **200** + original body on idempotent replay.
- Atomically debits receiver **available** balance; **409** `insufficient_funds` on failure; never reopens requests/authorizations or restores released holds.

## Single corrections (stage 3, unchanged scope)

- Ordinary direct/request payments remain correctable via stage-3 path.
- Capture and refund payments: **422** `linked_payment_immutable`.
- Correction cannot reduce amount below sum of refunds already taken: **422** `refund_exceeds_payment`; debits respect available funds.

## Correction batches

- `POST /correction-batches` — settlement operator + idempotency key; **401**/**403** same as settlements.
- Body: `{ "corrections": [ { "payment_id", "expected_revision", "amount", "effective_at", "reason" }, ... ] }`.
- **1..32** items, distinct `payment_id`; else **422** `validation_failed`.
- Per-item: stage-3 correction validation; unknown payment **404**; stale **409** `stale_revision`.
- Operator may batch-correct ordinary, request, and settlement payments; captures/refunds immutable.
- If any item is a settlement member, **every** member of that settlement must appear; else **422** `incomplete_settlement`.
- All members of one settlement in a batch must share the same effective instant (RFC3339 equality after normalization); else **422** `validation_failed`.
- Single-payment corrections still available for non-settlement members; unknown top-level fields ignored.

### Batch validation order

1. Item-level errors in **input order** (404, 422, 409 stale, immutable, etc.).
2. Settlement completeness (`incomplete_settlement`).
3. Combined effect on **current** available funds (`insufficient_funds`).
4. Historical total and available at every effective/event boundary (`historical_overdraft`, `refund_exceeds_payment`, etc.).

Rejected batch: no partial writes; history, balances, idempotency unchanged.

### Batch success and replay

- **201**: `correction_batch_id`, `recorded_at`, `revisions` (input order).
- All new revisions share one `recorded_at`, strictly after prior `recorded_at` of every touched payment; each revision includes `correction_batch_id`.
- `effective_at` must not be later than now.
- Original payment/settlement bodies on retry unchanged; statements show new revisions; existing snapshot tokens page frozen entries.
- Idempotent batch replay: **200** with original batch response.

## Settlements and refunds

- Settlement payments may be refunded under refund rules; refunds do not alter settlement membership.

## Concurrency and import

- Two concurrent corrections that share an `expected_revision` on any payment cannot both commit.
- Must accept exports from the same team’s stages 1–3 with settlement membership, corrections, and snapshots intact.

## Delivery

- `stage-4/` starts as copy of sealed `stage-3/` at rev **55207f5fd143**; include Dockerfile and RUN.md; official suites for stages 1–4 must pass in isolated mode at SUBMIT rev.
