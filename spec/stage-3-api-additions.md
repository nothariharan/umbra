# Pocketful Stage 3 — statements, corrections, temporal reads (extends stage 2)

Stage 1–2 API, UI, and invariants continue unless amended below.

## Payment timestamps

- Every payment includes RFC 3339 `created_at` with offset on every endpoint that returns a payment.
- `GET /activity` keeps ordering by `created_at`.
- Seeded payments may supply `created_at`; omission uses reset time before API-created payments.
- Future `created_at` on seed → `422 validation_failed` from `POST /_test/reset`, no state change.
- Fixture `balance` is post-all-seeded-payments; loading seeded payments must not change balances.

## Temporal `GET /me`

- Optional `as_of` (RFC 3339 with offset); naive date/bare/empty → `422 validation_failed`.
- Without temporal params: current corrected money fields unchanged from stage 2.
- With `as_of`: `balance` after all caller payments with `created_at <= as_of`; payment exactly at `as_of` counts.
- Edge cases: at/after latest → current; before earliest → opening balance; echo `as_of` exactly.

## `GET /statement`

- Query: optional `from`, `to` (default opening → now), `limit`, `offset` (same semantics as `GET /requests`).
- Window `[from, to)` half-open; entries oldest first by `created_at` then payment `id`.
- Each entry: `payment`, `delta` (sent negative, received positive), `balance_after` for caller.
- `opening_balance` before `from`; `closing_balance` before `to`; opening + sum(deltas) = closing in full window.
- Pagination must not alter per-entry `balance_after` or window opening/closing balances.
- Only caller’s sent/received payments (activity visibility rules do not apply).

## Corrections and revisions

- Effective vs recorded time; revision 1: original amount, `effective_at = recorded_at = created_at`.
- Seeded `created_at` is original effective/recorded; opening balances = seeded ending minus net original seeded payments; corrections must not change opening balances.
- `POST /payments/{id}/corrections` — idempotent; sender only; body fields and validation per spec; `403`/`404`/`422`/`409 stale_revision`/`409 insufficient_funds`/`409 historical_overdraft`.
- Idempotency: replay same key → `200` original body; different body same key → `409 idempotency_key_reuse`.
- Atomic wallet delta between same two parties; sum of balances equals seeded total in every historical view.
- `GET /activity` shows original payment only; corrections not new feed items.
- `GET /payments/{id}/revisions` — parties only, ordered revisions, rev1 `reason: ""`; third party `404`.

## `known_at` and corrected statements

- Optional `known_at` on `GET /me` and `GET /statement` (RFC 3339); invalid → `422`; echo when supplied.
- Select latest revision recorded at or before `known_at`; none recorded yet → payment omitted from view.
- Apply selected revisions by **effective** time; `as_of` inclusive; statement half-open window unchanged.
- Statement order: selected `effective_at`, then payment id; entries include selected `revision`, `effective_at`, `recorded_at`; `payment.amount` is selected amount; zero revisions appear with zero delta.
- No corrections + no `known_at` → stage 1–2 statement behavior where applicable.

## Snapshot pagination

- First `GET /statement` returns opaque `snapshot` token freezing revisions, window, balances, entries, default `to`.
- `GET /statement?snapshot=&limit=&offset=` pages exact frozen result; only limit/offset with snapshot; `from`/`to`/`known_at` with snapshot → `422 validation_failed`.
- Unknown/wrong-user/pre-reset token → `404 not_found`; tokens until reset; no cross-restart durability required.
- Concurrent payments/corrections do not mutate existing snapshots; concurrent corrections same expected revision cannot both succeed.

## Settlements and import

- Stage-1 settlements: member rev1 uses `committed_at` as effective and recorded.
- Single-payment correction of settlement member → `422 linked_payment_immutable`.
- Import stage-1/2 exports; ledger includes authorizations/captures; capture correction → `422 linked_payment_immutable`.

## Historical holds

- `GET /me?as_of=T&known_at=K`: `balance = total`, `available = total - held` for that view.
- Hold lifecycle times: creation, nonfinal capture, final capture/void/expiry at event times; expiry at `expires_at`; `closed_at` on authorizations.
- Corrections rejected with `409 historical_overdraft` if total or available negative at any past boundary under latest known revisions; current debit still `insufficient_funds` first.
- Seeded open holds assumed at reset unless `created_at` supplied.
- `GET /statement` — payments only (no auth/release/expiry rows); captures once with links; snapshots stable after lifecycle/correction.
