"""Breaker attack harness for Pocketful stage 3 (statements, corrections, temporal reads).

Extends the stage-2 harness (which extends stage-1) by path, so every stage-3 suite
reads the service address from BASE_URL exactly as the lever boots the submitted
revision. Only httpx, pytest, playwright and the standard library are used.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
for _p in (_HERE.parent / "stage-2", _HERE.parent / "stage-1"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from attacklib import (  # noqa: E402,F401
    BASE_URL,
    PASSWORD,
    Client,
    assert_error,
    assert_no_5xx,
    assert_status,
    assert_status_in,
    describe,
    do_reset,
    equal_split,
    error_code,
    fixture,
    new_client,
    new_key,
    race,
    seeded_total,
    user,
)
from attacklib2 import (  # noqa: E402,F401
    AuthClient,
    SHORT_TIMEOUT,
    authz,
    fixture2,
    fmt_amount,
    future_iso,
    new_auth_client,
    past_iso,
)

__all__ = [
    "BASE_URL", "PASSWORD", "Client", "AuthClient", "S3Client", "new_key", "race",
    "assert_status", "assert_status_in", "assert_error", "assert_no_5xx", "error_code",
    "describe", "do_reset", "seeded_total", "fixture", "fixture2", "fixture3", "user",
    "payment_seed", "authz", "now_utc", "iso", "plus", "minus", "at_offset", "parse_ts",
    "new_s3_client", "SHORT_TIMEOUT",
]

UTC = _dt.timezone.utc


def now_utc() -> _dt.datetime:
    return _dt.datetime.now(UTC)


def iso(dt: _dt.datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def plus(seconds: int) -> str:
    return iso(now_utc() + _dt.timedelta(seconds=seconds))


def minus(seconds: int) -> str:
    return iso(now_utc() - _dt.timedelta(seconds=seconds))


def at_offset(dt: _dt.datetime, hours: float) -> str:
    """The same instant written with a different explicit offset."""
    return iso(dt.astimezone(_dt.timezone(_dt.timedelta(hours=hours))))


def parse_ts(value: str) -> _dt.datetime:
    """RFC3339 with an explicit offset, or fail the attack."""
    assert isinstance(value, str) and value, f"timestamp must be a non-empty string: {value!r}"
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        parsed = _dt.datetime.fromisoformat(normalized)
    except ValueError:
        raise AssertionError(f"timestamp is not RFC3339: {value!r}") from None
    assert parsed.tzinfo is not None and parsed.utcoffset() is not None, \
        f"timestamp must carry an explicit offset: {value!r}"
    return parsed


def payment_seed(pid: str, frm: str, to: str, amount: int, *, created_at: str | None = None,
                 visibility: str = "public", note: str = "") -> dict:
    out: dict = {
        "payment_id": pid, "id": pid, "from_user_id": frm, "to_user_id": to,
        "amount": amount, "note": note, "visibility": visibility,
    }
    if created_at is not None:
        out["created_at"] = created_at
    return out


def fixture3(*, users=None, currency: str = "EUR", minor_units: int | None = None,
             payments=None, requests=None, operators=None, authorizations=None,
             ttl: int | None = None, include_authorizations: bool = True) -> dict:
    return fixture2(users=users, currency=currency, minor_units=minor_units,
                    payments=payments, requests=requests, operators=operators,
                    authorizations=authorizations, ttl=ttl,
                    include_authorizations=include_authorizations)


class S3Client(AuthClient):
    """A stage-3 client: temporal reads, statements, corrections and revisions."""

    def me_at(self, **params):
        return self.get("/me", params=params or None)

    def statement(self, **params):
        return self.get("/statement", params=params or None)

    def correct(self, payment_id: str, body: dict, *, key: str | None = None,
                key_sent: bool = True):
        headers = {}
        if key_sent:
            headers["Idempotency-Key"] = key or new_key()
        return self.post(f"/payments/{payment_id}/corrections", json=body, headers=headers)

    def revisions(self, payment_id: str):
        return self.get(f"/payments/{payment_id}/revisions")


def correction_body(expected_revision: int, amount: int, effective_at: str,
                    reason: str = "corrected amount") -> dict:
    return {"expected_revision": expected_revision, "amount": amount,
            "effective_at": effective_at, "reason": reason}


def revision_list(resp) -> list:
    body = resp.json()
    if isinstance(body, dict):
        for key in ("revisions", "items", "entries"):
            if isinstance(body.get(key), list):
                return body[key]
        raise AssertionError(f"revisions response has no list. {describe(resp)}")
    assert isinstance(body, list), f"revisions must be a list. {describe(resp)}"
    return body


def entries_of(resp) -> list:
    body = resp.json()
    assert isinstance(body, dict) and isinstance(body.get("entries"), list), \
        f"statement must carry entries[]. {describe(resp)}"
    return body["entries"]


def new_s3_client(token: str | None = None, timeout: float = SHORT_TIMEOUT) -> S3Client:
    return S3Client(token=token, timeout=timeout)
