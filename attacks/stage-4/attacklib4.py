"""Breaker attack harness for Pocketful stage 4 (refunds, batch corrections).

Extends the stage-3 harness by path, so every stage-4 suite reads the service
address from BASE_URL exactly as the lever boots the submitted revision. Only
httpx, pytest and the standard library are used.
"""
from __future__ import annotations

import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "stage-3", _HERE.parent / "stage-2", _HERE.parent / "stage-1"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from attacklib3 import (  # noqa: E402,F401
    BASE_URL,
    PASSWORD,
    Client,
    S3Client,
    at_offset,
    correction_body,
    entries_of,
    fixture3,
    iso,
    minus,
    new_key,
    parse_ts,
    payment_seed,
    plus,
    race,
    revision_list,
    assert_error,
    assert_no_5xx,
    assert_status,
    assert_status_in,
    authz,
    describe,
    do_reset,
    error_code,
    future_iso,
    new_s3_client,
    seeded_total,
    user,
    SHORT_TIMEOUT,
)
from attacklib3 import now_utc  # noqa: E402,F401

__all__ = [
    "BASE_URL", "PASSWORD", "Client", "S4Client", "new_s4_client", "new_key", "race",
    "assert_status", "assert_status_in", "assert_error", "assert_no_5xx", "error_code",
    "describe", "do_reset", "seeded_total", "fixture3", "user", "payment_seed", "authz",
    "correction_body", "entries_of", "revision_list", "parse_ts", "now_utc",
    "plus", "minus", "iso", "at_offset", "future_iso", "SHORT_TIMEOUT",
    "batch_item", "refund_seed", "revisions_of", "settlement_payments",
]


class S4Client(S3Client):
    """A stage-4 client: refunds and correction batches on top of stage-3 reads."""

    def refund(self, payment_id: str, amount: int | None = None, *, body: dict | None = None,
               key: str | None = None, key_sent: bool = True):
        payload = body if body is not None else {"amount": amount}
        headers = {}
        if key_sent:
            headers["Idempotency-Key"] = key or new_key()
        return self.post(f"/payments/{payment_id}/refunds", json=payload, headers=headers)

    def batch(self, corrections, *, key: str | None = None, key_sent: bool = True,
              extra: dict | None = None):
        payload = {"corrections": corrections}
        if extra:
            payload.update(extra)
        headers = {}
        if key_sent:
            headers["Idempotency-Key"] = key or new_key()
        return self.post("/correction-batches", json=payload, headers=headers)


def new_s4_client(token: str | None = None, timeout: float = SHORT_TIMEOUT) -> S4Client:
    return S4Client(token=token, timeout=timeout)


def batch_item(payment_id: str, expected_revision: int, amount: int, effective_at: str,
               reason: str = "batch correction") -> dict:
    return {"payment_id": payment_id, "expected_revision": expected_revision,
            "amount": amount, "effective_at": effective_at, "reason": reason}


def refund_seed(pid: str, frm: str, to: str, amount: int, *, refund_of: str,
                created_at: str | None = None, visibility: str = "public",
                note: str = "") -> dict:
    out = payment_seed(pid, frm, to, amount, created_at=created_at,
                       visibility=visibility, note=note)
    out["refund_of"] = refund_of
    return out


def revisions_of(resp) -> list:
    return revision_list(resp)


def settlement_payments(resp) -> list:
    body = resp.json()
    if isinstance(body, dict) and isinstance(body.get("payments"), list):
        return body["payments"]
    if isinstance(body, list):
        return body
    raise AssertionError(f"settlement response has no payments list. {describe(resp)}")
