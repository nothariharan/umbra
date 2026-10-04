"""Reference oracle for stage-3 statements, corrections, and temporal reads."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from s3lib import fixtures as fx
from s3lib.reference_model import ModelError, PocketfulReference, _parse_ts
from s3lib.temporal import parse_instant


@dataclass
class Revision:
    revision: int
    amount: int
    effective_at: datetime
    recorded_at: datetime
    reason: str


@dataclass
class PaymentLedger:
    payment_id: str
    from_user_id: str
    to_user_id: str
    visibility: str
    created_at: datetime
    revisions: list[Revision] = field(default_factory=list)
    settlement_id: str | None = None
    authorization_id: str | None = None
    immutable: bool = False

    def selected_revision(self, known_at: datetime | None) -> Revision | None:
        if not self.revisions:
            return None
        if known_at is None:
            return self.revisions[-1]
        eligible = [r for r in self.revisions if r.recorded_at <= known_at]
        if not eligible:
            return None
        return max(eligible, key=lambda r: r.revision)

    def amount_at(self, known_at: datetime | None) -> int | None:
        rev = self.selected_revision(known_at)
        return None if rev is None else rev.amount


@dataclass
class Stage3Reference(PocketfulReference):
    ledger: dict[str, PaymentLedger] = field(default_factory=dict)
    reset_at: datetime = field(default_factory=lambda: datetime(2026, 9, 24, 13, 0, tzinfo=timezone.utc))

    def reset(self, fixture: dict) -> None:
        super().reset(fixture)
        self.ledger = {}
        self.reset_at = self.now
        for pay in fixture.get("payments") or []:
            pid = pay["id"]
            created_raw = pay.get("created_at") or self.reset_at.isoformat(timespec="seconds")
            created = _parse_ts(created_raw)
            rev = Revision(1, int(pay["amount"]), created, created, "")
            self.ledger[pid] = PaymentLedger(
                payment_id=pid,
                from_user_id=pay["from_user_id"],
                to_user_id=pay["to_user_id"],
                visibility=pay.get("visibility", "public"),
                created_at=created,
                revisions=[rev],
                settlement_id=pay.get("settlement_id"),
                authorization_id=pay.get("authorization_id"),
                immutable=bool(pay.get("settlement_id")),
            )

    def opening_balance(self, user_id: str) -> int:
        u = next(u for u in self.users.values() if u["id"] == user_id)
        net = 0
        for p in self.ledger.values():
            rev = p.revisions[0]
            if p.from_user_id == user_id:
                net -= rev.amount
            if p.to_user_id == user_id:
                net += rev.amount
        return u["balance"] - net

    def _effective_events(self, user_id: str, known_at: datetime | None) -> list[tuple[datetime, str, int]]:
        events: list[tuple[datetime, str, int]] = []
        for p in self.ledger.values():
            rev = p.selected_revision(known_at)
            if rev is None:
                continue
            if p.from_user_id != user_id and p.to_user_id != user_id:
                continue
            delta = rev.amount if p.to_user_id == user_id else -rev.amount
            events.append((rev.effective_at, p.payment_id, delta))
        events.sort(key=lambda t: (t[0], t[1]))
        return events

    def balance_at(self, user_id: str, as_of: datetime, known_at: datetime | None = None) -> int:
        bal = self.opening_balance(user_id)
        for when, _pid, delta in self._effective_events(user_id, known_at):
            if when <= as_of:
                bal += delta
        return bal

    def apply_correction(
        self,
        sender_id: str,
        payment_id: str,
        *,
        expected_revision: int,
        amount: int,
        effective_at: datetime,
        recorded_at: datetime | None = None,
    ) -> Revision:
        pay = self.ledger.get(payment_id)
        if not pay:
            raise ModelError("not_found")
        if pay.from_user_id != sender_id:
            raise ModelError("forbidden")
        if pay.immutable:
            raise ModelError("linked_payment_immutable")
        latest = pay.revisions[-1]
        if latest.revision != expected_revision:
            raise ModelError("stale_revision")
        if amount < 0 or amount > 1_000_000_000:
            raise ModelError("validation_failed")
        if effective_at > self.now:
            raise ModelError("validation_failed")
        rec = recorded_at or self.now
        if rec <= latest.recorded_at:
            raise ModelError("validation_failed")
        prev = latest.amount
        delta = amount - prev
        if delta > 0:
            if self.available(sender_id) < delta:
                raise ModelError("insufficient_funds")
        elif delta < 0:
            receiver = pay.to_user_id
            if self.users[receiver]["balance"] < -delta:
                raise ModelError("insufficient_funds")
        trial_from = self.users[pay.from_user_id]["balance"] - max(delta, 0)
        trial_to = self.users[pay.to_user_id]["balance"] + max(-delta, 0)
        if trial_from < 0 or trial_to < 0:
            raise ModelError("historical_overdraft")
        if delta > 0:
            self.transfer(pay.from_user_id, pay.to_user_id, delta, check_available=True)
        elif delta < 0:
            self.transfer(pay.to_user_id, pay.from_user_id, -delta, check_available=False)
        new_rev = Revision(latest.revision + 1, amount, effective_at, rec, "corrected")
        pay.revisions.append(new_rev)
        return new_rev


def model_from_fixture(fixture: dict) -> Stage3Reference:
    m = Stage3Reference()
    m.reset(fixture)
    return m
