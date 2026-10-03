"""One-shot: record pocketful S1 requirements and rulings. Run from repo root."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

REQS = [
    ("S1-R1", "§2 Delivery", "Stage 1 deliverable is HTTP service source, Dockerfile, and RUN.md in stage-1/."),
    ("S1-R2", "§2 RUN.md", "RUN.md documents one command that builds and starts the service without manual setup."),
    ("S1-R3", "§3.1 Listen", "Service binds 0.0.0.0 on PORT env var, default 8080."),
    ("S1-R4", "§3.2 Health", "GET /health returns 200 with JSON {\"status\":\"ok\"} once ready, within 60s of container start."),
    ("S1-R5", "§3.3 Reset", "POST /_test/reset accepts fixture JSON, returns 204, replaces all state; repeated resets supported; no auth."),
    ("S1-R6", "§3.4 Conventions", "JSON charset utf-8; RFC3339 timestamps with offset; unknown body fields and query params ignored."),
    ("S1-R7", "§3.4 IDs", "Resource IDs are opaque strings of at most 64 characters."),
    ("S1-R8", "§1 Scope", "Users send money by handle, request money, split bills; activity feed with public/private visibility; operator settlements."),
    ("S1-R9", "§1 invariant", "Sum of wallet balances always equals total seeded by last successful POST /_test/reset."),
    ("S1-R10", "§1 invariant", "No wallet balance may be negative, including transiently during concurrent operations."),
    ("S1-R11", "§1 invariant", "A money request moves money at most once."),
    ("S1-R12", "§4 Arithmetic", "Amounts are integer minor units; max 1000000000 per operation; balances stay within ±2^53; exact integer arithmetic."),
    ("S1-R13", "§4 Currency", "Single currency from fixture; minor_units is 0, 2, or 3."),
    ("S1-R14", "§4 Handles", "Handles unique, match ^[a-z0-9_]{1,20}$, immutable once set."),
    ("S1-R15", "§4 Signup handle", "POST /auth/signup derives handle from email local part: lowercase, non [a-z0-9_] to _, truncate 20; 409 handle_taken if taken."),
    ("S1-R16", "§4 Fixture users", "Seeded users login with fixture password; balance is wallet after seeded payments applied without replaying payments."),
    ("S1-R17", "§4 Fixture reset", "Fixture balance below zero yields 422 validation_failed and no state change."),
    ("S1-R18", "§4 Payments/requests", "Payment moves money atomically; request pending then paid|declined|cancelled; payer pays/declines; requester cancels."),
    ("S1-R19", "§4 Request balance", "Creating a request does not require payer balance; pay while short returns 409 insufficient_funds unchanged."),
    ("S1-R20", "§4 Feed", "GET /activity returns payments only; visible if public or caller is sender or receiver; requests never in feed."),
    ("S1-R21", "§4 Visibility", "Payment visibility chosen by payer on direct pay or request pay; one value seen by all parties."),
    ("S1-R22", "§5 Errors", "Every 4xx/5xx returns {\"error\":{\"code\",\"message\"}} with specified status and code."),
    ("S1-R23", "§5 Shared fields", "Idempotency-Key 1-255 chars else 422; limit 1-200; offset >=0; bad integer query forms 422."),
    ("S1-R24", "§5 No 5xx", "Requests must not produce 5xx including under concurrent load."),
    ("S1-R25", "§6 Signup", "POST /auth/signup 201 with user_id, display_name, token; 409 email_taken; 422 short password or bad email."),
    ("S1-R26", "§6 Login", "POST /auth/login 200 on success; 401 unauthenticated on wrong password or unknown email."),
    ("S1-R27", "§6 Passwords", "Passwords stored with bcrypt, scrypt, Argon2 or equivalent; not plaintext."),
    ("S1-R28", "§6 Auth", "Bearer token required except /health, /_test/reset, /_test/export, /_test/import, signup, login; tokens do not expire."),
    ("S1-R29", "§7 Idempotency", "Five write paths require Idempotency-Key per §7 replay, reuse, concurrency, and post-4xx reuse rules."),
    ("S1-R30", "§8 GET /me", "Returns user_id, display_name, handle, balance, currency, minor_units."),
    ("S1-R31", "§8 POST /payments", "Idempotent debit/credit by to_handle; defaults note \"\" visibility public; cases insufficient_funds, self_payment, not_found, validation."),
    ("S1-R32", "§8 note", "Payment and request note stored and returned verbatim without trimming or normalization."),
    ("S1-R33", "§8 POST /requests", "Idempotent; caller is requester; self_request 422; payer balance not checked at creation."),
    ("S1-R34", "§8 pay request", "POST /requests/{id}/pay idempotent; payer only; 201 payment with request_id; replay 200 even when paid; visibility body default public."),
    ("S1-R35", "§8 decline/cancel", "Decline/cancel idempotent 200 on repeat; 409 request_not_pending when paid/declined/cancelled wrongly; 403 when wrong party."),
    ("S1-R36", "§8 GET /requests", "Lists caller as requester or payer; direction incoming|outgoing; status filter; newest first; has_more; limit/offset defaults."),
    ("S1-R37", "§8 POST /splits", "Idempotent equal-split requests for every participant except caller; shares array order; zero-share still creates request."),
    ("S1-R38", "§9 Split rounding", "Shares whole minor units, sum to amount, differ by at most 1; remainder to earliest handles in participant_handles order."),
    ("S1-R39", "§8 GET /activity", "Visible payments newest first; limit/offset; has_more."),
    ("S1-R40", "§10 Export", "GET /_test/export returns track pocketful, format_version 1, opaque state snapshot."),
    ("S1-R41", "§10 Import", "POST /_test/import accepts export object atomically 204; invalid JSON/track/version/state 422 unchanged; round-trip preserves tokens, idempotency, balances, timestamps."),
    ("S1-R42", "§11 Settlements", "POST /settlements operator-only idempotent; 1-32 transfers atomic; 404 unknown handle; 422 self_payment; 409 insufficient_funds collective; 201 with settlement_id, committed_at, payments in order."),
    ("S1-R43", "§11 Operators", "Fixture settlement_operator_ids grants settlement permission only; not other users' private activity or requests."),
    ("S1-R44", "§2 Docker", "Image runs with -e PORT and port mapping; runtime no outbound network; all deps and seed in container."),
    ("S1-R45", "§2 Limits", "Operates within 2 vCPU, 2 GiB, 50 concurrent, 5s timeout (10s reset/import), no compose at runtime."),
    ("S1-R46", "§8 amounts", "JSON amounts accept integral forms 1000, 1000.0, 1e3; strings/booleans invalid amount 422."),
]

RULINGS = [
    ("S1-U1", "S1-R34", "Empty body {} and {\"visibility\":\"public\"} are distinct JSON for idempotency on POST /requests/{id}/pay."),
    ("S1-U2", "S1-R29", "After auth and JSON object parse, idempotency key resolution precedes endpoint field validation."),
    ("S1-U3", "S1-R31", "self_payment on POST /payments uses code self_payment at 422 per endpoint table, not generic validation_failed."),
    ("S1-U4", "S1-R33", "self_request on POST /requests uses code self_request at 422."),
    ("S1-U5", "S1-R1,S1-R2", "SUBMIT rev must be a git commit containing stage-1/ via scripts/commit.py --seat builder."),
]


def main():
    for rid, src, text in REQS:
        subprocess.check_call(
            [PY, "scripts/record.py", "requirement", "--seat", "lead", "--id", rid,
             "--stage", "1", "--source", src, "--text", text],
            cwd=ROOT,
        )
    for uid, req, text in RULINGS:
        subprocess.check_call(
            [PY, "scripts/record.py", "ruling", "--seat", "lead", "--id", uid,
             "--req", req, "--text", text],
            cwd=ROOT,
        )
    print("seeded", len(REQS), "requirements,", len(RULINGS), "rulings")


if __name__ == "__main__":
    main()
