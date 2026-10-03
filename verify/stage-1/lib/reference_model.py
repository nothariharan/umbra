"""In-memory oracle for Pocketful Stage 1 monetary and request rules."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from lib import fixtures as fx


class ModelError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass
class PocketfulReference:
    currency: str = "EUR"
    minor_units: int = 2
    users: dict[str, dict] = field(default_factory=dict)
    handles: dict[str, str] = field(default_factory=dict)
    requests: dict[str, dict] = field(default_factory=dict)
    payments: list[dict] = field(default_factory=list)
    operators: set[str] = field(default_factory=set)
    seeded_total: int = 0
    _seq: int = 0

    def reset(self, fixture: dict) -> None:
        self.currency = fixture["currency"]
        self.minor_units = fixture["minor_units"]
        self.users = {u["id"]: dict(u) for u in fixture["users"]}
        self.handles = {u["handle"]: u["id"] for u in self.users.values()}
        self.operators = set(fixture.get("settlement_operator_ids") or [])
        self.seeded_total = sum(u["balance"] for u in self.users.values())
        self.requests = {}
        self.payments = []
        self._seq = 0
        for rq in fixture.get("requests") or []:
            self.requests[rq["id"]] = dict(rq)

    def _id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq}"

    def balance(self, user_id: str) -> int:
        return self.users[user_id]["balance"]

    def conservation_ok(self) -> bool:
        return sum(u["balance"] for u in self.users.values()) == self.seeded_total

    def all_non_negative(self) -> bool:
        return all(u["balance"] >= 0 for u in self.users.values())

    def transfer(self, from_id: str, to_id: str, amount: int) -> None:
        if amount < 1 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        if from_id == to_id:
            raise ModelError("self_payment")
        if self.users[from_id]["balance"] < amount:
            raise ModelError("insufficient_funds")
        self.users[from_id]["balance"] -= amount
        self.users[to_id]["balance"] += amount
        if not self.all_non_negative():
            raise ModelError("negative_balance")

    def pay_handle(self, from_id: str, to_handle: str, amount: int) -> None:
        if to_handle not in self.handles:
            raise ModelError("not_found")
        self.transfer(from_id, self.handles[to_handle], amount)

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
        self.transfer(payer_id, rq["requester_id"], rq["amount"])
        pid = self._id("p")
        rq["status"] = "paid"
        rq["payment_id"] = pid

    def decline_request(self, payer_id: str, request_id: str) -> None:
        rq = self.requests.get(request_id)
        if not rq:
            raise ModelError("not_found")
        if rq["payer_id"] != payer_id:
            raise ModelError("forbidden")
        if rq["status"] in ("paid", "cancelled"):
            raise ModelError("request_not_pending")
        rq["status"] = "declined"

    def cancel_request(self, requester_id: str, request_id: str) -> None:
        rq = self.requests.get(request_id)
        if not rq:
            raise ModelError("not_found")
        if rq["requester_id"] != requester_id:
            raise ModelError("forbidden")
        if rq["status"] in ("paid", "declined"):
            raise ModelError("request_not_pending")
        rq["status"] = "cancelled"

    def split(self, caller_id: str, amount: int, participant_handles: list[str]) -> list[int]:
        if amount < 1 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        if not participant_handles or len(participant_handles) != len(set(participant_handles)):
            raise ModelError("validation_failed")
        for h in participant_handles:
            if h not in self.handles:
                raise ModelError("not_found")
        shares = fx.equal_split(amount, len(participant_handles))
        created: list[str] = []
        caller_handle = self.users[caller_id]["handle"]
        for handle, share in zip(participant_handles, shares):
            if handle == caller_handle:
                continue
            created.append(self.create_request(caller_id, handle, share))
        return shares

    def settle(self, transfers: list[dict]) -> None:
        if not (1 <= len(transfers) <= 32):
            raise ModelError("validation_failed")
        deltas: dict[str, int] = {uid: 0 for uid in self.users}
        for t in transfers:
            fh, th, amt = t["from_handle"], t["to_handle"], int(t["amount"])
            if fh not in self.handles or th not in self.handles:
                raise ModelError("not_found")
            if fh == th:
                raise ModelError("self_payment")
            if amt < 1 or amt > 1_000_000_000:
                raise ModelError("validation_failed")
            f_id, t_id = self.handles[fh], self.handles[th]
            deltas[f_id] -= amt
            deltas[t_id] += amt
        for uid, bal in self.users.items():
            if bal["balance"] + deltas[uid] < 0:
                raise ModelError("insufficient_funds")
        for t in transfers:
            self.transfer(self.handles[t["from_handle"]], self.handles[t["to_handle"]], int(t["amount"]))

    def snapshot_balances(self) -> dict[str, int]:
        return {uid: u["balance"] for uid, u in self.users.items()}


def model_from_fixture(fixture: dict) -> PocketfulReference:
    m = PocketfulReference()
    m.reset(fixture)
    return m
