# Pocketful Stage 1 — HTTP API contract

Base URL: `http://host:PORT` where the service binds `0.0.0.0` and `PORT` defaults to `8080`.

All request/response bodies are JSON (`application/json; charset=utf-8`). Timestamps are RFC 3339 with explicit offset.

## Unauthenticated

| Method | Path | Success | Notes |
|--------|------|---------|-------|
| GET | `/health` | 200 `{"status":"ok"}` | Ready within 60s of container start |
| POST | `/_test/reset` | 204 empty | Full fixture replace; 422 on invalid fixture |
| GET | `/_test/export` | 200 | `track`, `format_version`, `state` |
| POST | `/_test/import` | 204 | Atomic replace from export object |
| POST | `/auth/signup` | 201 user + token | |
| POST | `/auth/login` | 200 user + token | |

## Authenticated (`Authorization: Bearer <token>`)

| Method | Path | Idempotency-Key | Success |
|--------|------|-----------------|---------|
| GET | `/me` | — | 200 profile + balance |
| POST | `/payments` | required | 201 payment |
| POST | `/requests` | required | 201 request |
| POST | `/requests/{id}/pay` | required | 201 payment |
| POST | `/requests/{id}/decline` | — | 200 request |
| POST | `/requests/{id}/cancel` | — | 200 request |
| GET | `/requests` | — | 200 list |
| POST | `/splits` | required | 201 split |
| GET | `/activity` | — | 200 payments list |
| POST | `/settlements` | required (operators only) | 201 settlement |

## Error body (all 4xx/5xx)

```json
{"error":{"code":"<code>","message":"<human readable>"}}
```

## Payment object (response)

`payment_id`, `from_user_id`, `from_handle`, `to_user_id`, `to_handle`, `amount`, `currency`, `note`, `visibility`, `request_id`, `created_at`, optional `settlement_id` on settlement members.

## Request object (response)

`request_id`, `requester_id`, `requester_handle`, `payer_id`, `payer_handle`, `amount`, `currency`, `note`, `status`, `payment_id`, `created_at`.

## Fixture (POST /_test/reset)

`currency`, `minor_units` (0|2|3), `users[]`, optional `payments[]`, `requests[]`, optional `settlement_operator_ids[]` (default []).

User: `id`, `email`, `password`, `display_name`, `handle`, `balance` (after seeded payments applied).
