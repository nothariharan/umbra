"""Breaker attack harness for Pocketful stage 2 (authorizations, captures, UI races).

Reuses the stage-1 attack library (imported by path) so every stage-2 suite reads the
service address from BASE_URL exactly as the lever boots the submitted revision.
Only httpx, pytest, the standard library and playwright are used.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "stage-1"))

import attacklib as s1  # noqa: E402
from attacklib import (  # noqa: E402,F401
    BASE_URL,
    Client,
    PASSWORD,
    REQUEST_TIMEOUT,
    RESET_TIMEOUT,
    assert_error,
    assert_status,
    assert_status_in,
    describe,
    do_reset,
    equal_split,
    error_code,
    fixture,
    new_key,
    race,
    seeded_total,
)
from attacklib import user as s1_user  # noqa: E402

__all__ = [
    "BASE_URL", "Client", "PASSWORD", "new_key", "race", "equal_split",
    "assert_status", "assert_status_in", "assert_error", "error_code", "describe",
    "do_reset", "seeded_total", "s1_user", "fixture2", "authz", "future_iso",
    "past_iso", "fmt_amount", "AuthClient", "new_auth_client", "SHORT_TIMEOUT",
]

# Captures and holds are fast, but a deliberate lost-response retry can take a moment.
SHORT_TIMEOUT = 8.0


def now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def iso(dt: _dt.datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def future_iso(seconds: int = 3600) -> str:
    return iso(now_utc() + _dt.timedelta(seconds=seconds))


def past_iso(seconds: int = 3600) -> str:
    return iso(now_utc() - _dt.timedelta(seconds=seconds))


def authz(aid: str, from_uid: str, to_uid: str, amount: int, *, status: str = "open",
          expires_at: str | None = None, note: str = "", visibility: str = "private",
          captured_amount: int | None = None, payment_id: str | None = None,
          payment_ids: list[str] | None = None, created_at: str | None = None) -> dict:
    out: dict = {
        "id": aid, "from_user_id": from_uid, "to_user_id": to_uid,
        "amount": amount, "note": note, "visibility": visibility,
        "status": status, "expires_at": expires_at or future_iso(),
    }
    if captured_amount is not None:
        out["captured_amount"] = captured_amount
    if payment_id is not None:
        out["payment_id"] = payment_id
    if payment_ids is not None:
        out["payment_ids"] = payment_ids
    if created_at is not None:
        out["created_at"] = created_at
    return out


def fixture2(*, users=None, currency: str = "EUR", minor_units: int | None = None,
             payments=None, requests=None, operators=None,
             authorizations=None, ttl: int | None = None,
             include_authorizations: bool = True) -> dict:
    """A stage-1 fixture plus the stage-2 authorization fields."""
    body = fixture(
        users=users, currency=currency, minor_units=minor_units, payments=payments,
        requests=requests, operators=operators,
    )
    if include_authorizations:
        body["authorizations"] = authorizations if authorizations is not None else []
    if ttl is not None:
        body["authorization_ttl_seconds"] = ttl
    return body


def fmt_amount(amount: int, currency: str, minor_units: int) -> str:
    if minor_units == 0:
        return f"{amount} {currency}"
    neg = amount < 0
    digits = str(abs(amount)).rjust(minor_units + 1, "0")
    whole, frac = digits[:-minor_units], digits[-minor_units:]
    return f"{'-' if neg else ''}{whole}.{frac} {currency}"


class AuthClient(Client):
    """A stage-2 client: holds, captures, voids and the new /me read."""

    def me_full(self) -> dict:
        resp = self.get("/me")
        assert resp.status_code == 200, describe(resp)
        return resp.json()

    def wallet(self) -> tuple[int, int, int]:
        body = self.me_full()
        total = body.get("total", body.get("balance"))
        return body["balance"], total, body["available"], body["held"]  # type: ignore[return-value]

    def authorize(self, to_handle: str, amount: int, *, key: str | None = None,
                  note: str | None = None, visibility: str | None = None,
                  key_sent: bool = True) -> "httpx.Response":  # noqa: F821
        body: dict = {"to_handle": to_handle, "amount": amount}
        if note is not None:
            body["note"] = note
        if visibility is not None:
            body["visibility"] = visibility
        headers = {}
        if key_sent:
            headers["Idempotency-Key"] = key or new_key()
        return self.post("/authorizations", json=body, headers=headers)

    def capture(self, aid: str, amount: int | None = None, *, key: str | None = None,
                final: bool | None = None, body: dict | None = None,
                key_sent: bool = True) -> "httpx.Response":  # noqa: F821
        if body is None:
            body = {}
            if amount is not None:
                body["amount"] = amount
            if final is not None:
                body["final"] = final
        headers = {}
        if key_sent:
            headers["Idempotency-Key"] = key or new_key()
        return self.post(f"/authorizations/{aid}/capture", json=body, headers=headers)

    def void(self, aid: str) -> "httpx.Response":  # noqa: F821
        return self.post(f"/authorizations/{aid}/void")

    def list_authorizations(self, **params) -> "httpx.Response":  # noqa: F821
        return self.get("/authorizations", params=params or None)

    def find_authorization(self, aid: str) -> dict | None:
        resp = self.list_authorizations(limit=200)
        assert resp.status_code == 200, describe(resp)
        body = resp.json()
        items = body.get("authorizations") if isinstance(body, dict) else body
        assert isinstance(items, list), f"GET /authorizations must be a list. {describe(resp)}"
        for item in items:
            if item.get("authorization_id", item.get("id")) == aid:
                return item
        return None


def new_auth_client(token: str | None = None, timeout: float = SHORT_TIMEOUT) -> AuthClient:
    return AuthClient(token=token, timeout=timeout)
