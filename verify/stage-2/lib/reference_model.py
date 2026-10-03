"""In-memory oracle for Pocketful Stage 2 (extends stage 1 with authorizations)."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from lib import fixtures as fx


class ModelError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


@dataclass
class PocketfulReference:
    currency: str = "EUR"
    minor_units: int = 2
    auth_ttl: int = 600
    users: dict[str, dict] = field(default_factory=dict)
    handles: dict[str, str] = field(default_factory=dict)
    requests: dict[str, dict] = field(default_factory=dict)
    payments: list[dict] = field(default_factory=list)
    authorizations: dict[str, dict] = field(default_factory=dict)
    operators: set[str] = field(default_factory=set)
    seeded_total: int = 0
    now: datetime = field(default_factory=lambda: datetime(2026, 9, 24, 13, 0, tzinfo=timezone.utc))
    _seq: int = 0

    def reset(self, fixture: dict) -> None:
        self.currency = fixture["currency"]
        self.minor_units = fixture["minor_units"]
        self.auth_ttl = int(fixture.get("authorization_ttl_seconds") or 600)
        self.users = {u["id"]: dict(u) for u in fixture["users"]}
        self.handles = {u["handle"]: u["id"] for u in self.users.values()}
        self.operators = set(fixture.get("settlement_operator_ids") or [])
        self.seeded_total = sum(u["balance"] for u in self.users.values())
        self.requests = {}
        self.payments = []
        self.authorizations = {}
        self._seq = 0
        for rq in fixture.get("requests") or []:
            self.requests[rq["id"]] = dict(rq)
        for auth in fixture.get("authorizations") or []:
            row = dict(auth)
            self.authorizations[row["id"]] = row
            self._refresh_auth_status(row)

    def _id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq}"

    def _refresh_auth_status(self, auth: dict) -> None:
        if auth.get("status") != "open":
            return
        exp = _parse_ts(auth["expires_at"])
        if exp <= self.now:
            auth["status"] = "expired"

    def held_for(self, user_id: str) -> int:
        total = 0
        for auth in self.authorizations.values():
            self._refresh_auth_status(auth)
            if auth.get("status") != "open" or auth["from_user_id"] != user_id:
                continue
            captured = int(auth.get("captured_amount") or 0)
            total += int(auth["amount"]) - captured
        return total

    def available(self, user_id: str) -> int:
        return self.users[user_id]["balance"] - self.held_for(user_id)

    def balance(self, user_id: str) -> int:
        return self.users[user_id]["balance"]

    def conservation_ok(self) -> bool:
        return sum(u["balance"] for u in self.users.values()) == self.seeded_total

    def all_non_negative(self) -> bool:
        return all(u["balance"] >= 0 for u in self.users.values())

    def transfer(self, from_id: str, to_id: str, amount: int, *, check_available: bool = True) -> None:
        if amount < 1 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        if from_id == to_id:
            raise ModelError("self_payment")
        spendable = self.available(from_id) if check_available else self.users[from_id]["balance"]
        if spendable < amount:
            raise ModelError("insufficient_funds")
        self.users[from_id]["balance"] -= amount
        self.users[to_id]["balance"] += amount
        if not self.all_non_negative():
            raise ModelError("negative_balance")

    def pay_handle(self, from_id: str, to_handle: str, amount: int) -> None:
        if to_handle not in self.handles:
            raise ModelError("not_found")
        self.transfer(from_id, self.handles[to_handle], amount, check_available=True)

    def create_authorization(self, from_id: str, to_handle: str, amount: int) -> str:
        if to_handle not in self.handles:
            raise ModelError("not_found")
        to_id = self.handles[to_handle]
        if to_id == from_id:
            raise ModelError("self_payment")
        if amount < 1 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        if self.available(from_id) < amount:
            raise ModelError("insufficient_funds")
        aid = self._id("a")
        created = self.now
        expires = created + timedelta(seconds=self.auth_ttl)
        self.authorizations[aid] = {
            "id": aid,
            "from_user_id": from_id,
            "to_user_id": to_id,
            "amount": amount,
            "captured_amount": 0,
            "status": "open",
            "expires_at": expires.isoformat(timespec="seconds"),
            "created_at": created.isoformat(timespec="seconds"),
        }
        return aid

    def _remaining(self, auth: dict) -> int:
        return int(auth["amount"]) - int(auth.get("captured_amount") or 0)

    def capture(self, receiver_id: str, auth_id: str, amount: int | None, *, final: bool = True) -> None:
        auth = self.authorizations.get(auth_id)
        if not auth:
            raise ModelError("not_found")
        self._refresh_auth_status(auth)
        if auth["to_user_id"] != receiver_id:
            raise ModelError("forbidden")
        if auth["status"] != "open":
            raise ModelError("authorization_not_open")
        if _parse_ts(auth["expires_at"]) <= self.now:
            auth["status"] = "expired"
            raise ModelError("authorization_expired")
        rem = self._remaining(auth)
        cap = rem if amount is None else amount
        if cap < 1:
            raise ModelError("validation_failed")
        if cap > rem:
            raise ModelError("capture_exceeds_authorization")
        payer = auth["from_user_id"]
        self.transfer(payer, receiver_id, cap, check_available=False)
        auth["captured_amount"] = int(auth.get("captured_amount") or 0) + cap
        if final or self._remaining(auth) == 0:
            auth["status"] = "captured"
        if auth["status"] == "captured" and self._remaining(auth) > 0:
            pass  # remainder released implicitly (not held)

    def void(self, payer_id: str, auth_id: str) -> None:
        auth = self.authorizations.get(auth_id)
        if not auth:
            raise ModelError("not_found")
        self._refresh_auth_status(auth)
        if auth["from_user_id"] != payer_id:
            raise ModelError("forbidden")
        if auth["status"] == "voided":
            return
        if auth["status"] != "open":
            raise ModelError("authorization_not_open")
        auth["status"] = "voided"

    def create_request(self, requester_id: str, payer_handle: str, amount: int) -> str:
        if payer_handle not in self.handles:
            raise ModelError("not_found")
        payer_id = self.handles[payer_handle]
        if payer_id == requester_id:
            raise ModelError("self_request")
        if amount < 1 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        rid = self._id("rq")
        self.requests[rid] = {
            "id": rid,
            "requester_id": requester_id,
            "payer_id": payer_id,
            "amount": amount,
            "status": "pending",
            "payment_id": None,
        }
        return rid

    def pay_request(self, payer_id: str, request_id: str) -> None:
        rq = self.requests.get(request_id)
        if not rq:
            raise ModelError("not_found")
        if rq["payer_id"] != payer_id:
            raise ModelError("forbidden")
        if rq["status"] != "pending":
            raise ModelError("request_not_pending")
        self.transfer(payer_id, rq["requester_id"], rq["amount"], check_available=True)
        rq["status"] = "paid"
        rq["payment_id"] = self._id("p")

    def split(self, caller_id: str, amount: int, participant_handles: list[str]) -> list[int]:
        if amount < 1 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        if not participant_handles or len(participant_handles) != len(set(participant_handles)):
            raise ModelError("validation_failed")
        for h in participant_handles:
            if h not in self.handles:
                raise ModelError("not_found")
        shares = fx.equal_split(amount, len(participant_handles))
        caller_handle = self.users[caller_id]["handle"]
        for handle, share in zip(participant_handles, shares):
            if handle == caller_handle:
                continue
            self.create_request(caller_id, handle, share)
        return shares


def model_from_fixture(fixture: dict) -> PocketfulReference:
    m = PocketfulReference()
    m.reset(fixture)
    return m
