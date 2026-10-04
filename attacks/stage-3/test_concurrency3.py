"""S3-R18, R23, R30-class: concurrency on corrections, snapshots and temporal reads."""
from __future__ import annotations

from attacklib3 import (
    assert_status,
    fixture3,
    new_key,
    race,
)

PASSWORD = "correct horse"


def _users(ada=100000, bob=500):
    return [
        {"id": "u_ada", "email": "ada@example.com", "password": PASSWORD,
         "display_name": "Ada", "handle": "ada", "balance": ada},
        {"id": "u_bob", "email": "bob@example.com", "password": PASSWORD,
         "display_name": "Bob", "handle": "bob", "balance": bob},
    ]


def test_concurrent_corrections_on_distinct_payments_conserve_total(world3):
    before_total = sum(c.me_full()["balance"] for c in world3.all)
    payments = [
        assert_status(world3.ada.post(
            "/payments", json={"to_handle": "bob", "amount": 100},
            headers={"Idempotency-Key": new_key()}), 201).json()
        for _ in range(5)
    ]

    def attempt(i):
        return world3.ada.correct(payments[i]["payment_id"], {
            "expected_revision": 1, "amount": 150 + i,
            "effective_at": payments[i]["created_at"], "reason": "batch"})

    results = race(attempt, len(payments))
    assert all(r.status_code == 201 for r in results), \
        f"distinct corrections must all commit: {[r.status_code for r in results]}"
    assert sum(c.me_full()["balance"] for c in world3.all) == before_total


def test_concurrent_temporal_reads_never_5xx(world3):
    calls = []
    for _ in range(20):
        calls.append(("me", lambda c=world3.ada: c.me_at(as_of="2026-09-24T08:00:00+00:00")))
        calls.append(("statement", lambda c=world3.ada: c.statement(limit=10)))

    def attempt(i):
        _, fn = calls[i % len(calls)]
        return fn()

    results = race(attempt, 40)
    for resp in results:
        assert resp.status_code < 500, f"a concurrent read returned 5xx: {resp.text}"
        assert resp.status_code == 200, f"a concurrent read failed: {resp.status_code}"


def test_concurrent_payments_do_not_corrupt_statement_balances(world3):
    keys = [new_key() for _ in range(12)]

    def attempt(i):
        return world3.ada.post("/payments", json={"to_handle": "bob", "amount": 10},
                               headers={"Idempotency-Key": keys[i]})

    results = race(attempt, len(keys))
    assert all(r.status_code == 201 for r in results), \
        f"all distinct concurrent payments must commit: {[r.status_code for r in results]}"
    body = assert_status(world3.ada.statement(limit=200), 200).json()
    assert body["opening_balance"] + sum(e["delta"] for e in body["entries"]) == \
        body["closing_balance"], "opening + deltas must equal closing under concurrency"
    assert body["closing_balance"] == world3.ada.balance()
