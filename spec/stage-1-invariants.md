# Pocketful Stage 1 — invariants and mechanisms

## Monetary (always, including concurrency and retries)

1. **Conservation:** Sum of all wallet balances equals total seeded by the last successful `POST /_test/reset`.
2. **Non-negative:** No wallet balance may go below zero at any time (including mid-transaction).
3. **Request pay-once:** A money request may cause at most one successful payment (state `paid` with one `payment_id`).

## Idempotency (five write paths)

Paths: `POST /payments`, `POST /requests`, `POST /requests/{id}/pay`, `POST /splits`, `POST /settlements`.

- Key scoped per authenticated user; length 1–255 (else 422).
- Same user+method+path+parsed JSON body + key → 200 with original response body; no extra state change.
- Same key, different body → 409 `idempotency_key_reuse`.
- Missing/empty header → 400 `missing_idempotency_key`.
- Concurrent first use: exactly one 201, others 200 identical.
- After original 4xx failure, key is reusable as first use.
- After auth and JSON parse, claimed-key resolution runs before endpoint field validation.

## Activity feed

Payment visible iff `visibility` is `public` OR caller is sender OR receiver. Requests never appear in `/activity`.

## Split shares

Equal split among `participant_handles` in order; shares are whole minor units, sum to `amount`, differ by at most 1; larger shares to earlier handles when remainder exists.

## Settlements

Operator-only (`settlement_operator_ids` from fixture). 1–32 transfers; all commit atomically or none; affordability checked on collective post-batch balances.

## Export/import

Export snapshot is read-only; import replaces entire state and must round-trip unchanged export. Preserves tokens, idempotency records, timestamps, balances without replaying payments.
