# Pocketful Stage 2 — API additions (extends stage 1)

Stage 1 API and invariants continue unless amended below.

## Wallet fields (`GET /me`)

- `balance` equals `total`.
- `available = total − held`; `held` is sum of open authorization holds; never negative available.

## Authorizations

- `POST /authorizations` — idempotent; payer; holds `available`; not in activity feed.
- `POST /authorizations/{id}/capture` — idempotent; receiver only; creates payment with `authorization_id`; default final capture releases remainder; optional `final: false` extended mode.
- `POST /authorizations/{id}/void` — payer only; no idempotency key.
- `GET /authorizations` — caller payer or receiver; direction/status/limit/offset like requests.

## Fixture additions

- `authorization_ttl_seconds` (default 600); `authorizations[]` with statuses open|captured|voided|expired.
- Seeded holds cannot exceed user balance; `available` derived not seeded.
- Expired by clock at read time; `GET /me` reflects released funds.

## Stage 1 deltas

- `409 insufficient_funds` uses **available** not total when holds exist.
- Seven idempotent writes: stage-1 five + authorizations + captures.
- `POST /payments` remains immediate transfer (no hold).

## Content negotiation

- `/requests` and `/authorizations`: `Accept: text/html` → UI; else JSON API.
