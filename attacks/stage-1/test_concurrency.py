"""Concurrency attacks: shared money moved by simultaneous requests.

Class: concurrency. Every test here fires overlapping requests on purpose, so a
check made before an action that no longer holds when the action runs shows up as
overspend, double payment or a lost update.
"""
from __future__ import annotations

from attacklib import (
    assert_error, assert_no_5xx, fixture, new_key, race, user,
)

PAY = "/payments"


def _pay(api, *, to_handle, amount, key=None, **extra):
    body = {"to_handle": to_handle, "amount": amount}
    body.update(extra)
    c = api()
    return c.post(PAY, json=body, headers={"Idempotency-Key": key or new_key()})


def test_concurrent_payments_never_overspend(boot, api):
    """1000 available, 50 simultaneous payments of 100: exactly 10 may succeed."""
    w = boot(fixture(users=[user("ada", 1000), user("bob", 0)]), handles=("ada", "bob"))

    def one(i):
        c = api()
        return c.post(PAY, json={"to_handle": "bob", "amount": 100},
                      headers={"Idempotency-Key": new_key()})

    results = race(one, 50)
    for r in results:
        assert_no_5xx(r)
    codes = [r.status_code for r in results]
    assert codes.count(201) == 10, f"expected 10 winners, got {codes}"
    assert all(c in (201, 409) for c in codes), codes
    for r in results:
        if r.status_code != 201:
            assert_error(r, 409, "insufficient_funds")
    assert w.ada.balance() == 0, "overspend: payer went below zero or short-changed"
    assert w.bob.balance() == 1000, "credits do not match the 10 debits"
    assert w.ada.balance() + w.bob.balance() == w.total


def test_concurrent_same_key_payment_moves_money_once(boot, api):
    """30 simultaneous identical requests with one unused key: one effect, one 201."""
    w = boot(fixture(users=[user("ada", 1000), user("bob", 0)]), handles=("ada", "bob"))
    key = new_key()
    payload = {"to_handle": "bob", "amount": 100}

    def one(i):
        c = api()
        return c.post(PAY, json=payload, headers={"Idempotency-Key": key})

    results = race(one, 30)
    for r in results:
        assert_no_5xx(r)
    codes = [r.status_code for r in results]
    assert codes.count(201) == 1, f"exactly one first-use must win: {codes}"
    assert all(c in (200, 201) for c in codes), codes
    bodies = [r.json() for r in results]
    assert all(b == bodies[0] for b in bodies), "replays returned a different body"
    assert len({b["payment_id"] for b in bodies}) == 1, "more than one payment was created"
    assert w.ada.balance() == 900, "the payment was applied more than once"
    assert w.bob.balance() == 100


def test_concurrent_pay_request_moves_money_once(boot, api):
    """One request, 30 simultaneous pays with distinct keys: exactly one payment."""
    w = boot(fixture(users=[user("ada", 1000), user("bob", 0)]), handles=("ada", "bob"))
    made = w.bob.post("/requests", json={"payer_handle": "ada", "amount": 100},
                      headers={"Idempotency-Key": new_key()})
    assert made.status_code == 201, made.text
    rid = made.json()["request_id"]

    def one(i):
        c = api()
        return c.post(f"/requests/{rid}/pay", json={},
                      headers={"Idempotency-Key": new_key()})

    results = race(one, 30)
    for r in results:
        assert_no_5xx(r)
    codes = [r.status_code for r in results]
    assert codes.count(201) == 1, f"a request may move money once: {codes}"
    for r in results:
        if r.status_code != 201:
            assert_error(r, 409, "request_not_pending")
    assert w.ada.balance() == 900
    assert w.bob.balance() == 100
    listed = w.bob.get("/requests").json()["requests"]
    req = next(q for q in listed if q["request_id"] == rid)
    assert req["status"] == "paid"
    assert req["payment_id"], "paid request must carry its payment_id"


def test_concurrent_pay_request_same_key(boot, api):
    """One request paid 30 times with the same key: replays are 200, money once."""
    w = boot(fixture(users=[user("ada", 1000), user("bob", 0)]), handles=("ada", "bob"))
    made = w.bob.post("/requests", json={"payer_handle": "ada", "amount": 100},
                      headers={"Idempotency-Key": new_key()})
    assert made.status_code == 201, made.text
    rid = made.json()["request_id"]
    key = new_key()

    def one(i):
        c = api()
        return c.post(f"/requests/{rid}/pay", json={}, headers={"Idempotency-Key": key})

    results = race(one, 30)
    for r in results:
        assert_no_5xx(r)
    codes = [r.status_code for r in results]
    assert codes.count(201) == 1, codes
    assert all(c in (200, 201) for c in codes), codes
    bodies = [r.json() for r in results]
    assert all(b == bodies[0] for b in bodies)
    assert w.ada.balance() == 900
    assert w.bob.balance() == 100


def test_concurrent_settlements_cannot_overspend(boot, api):
    """Two settlements each need 600 from a wallet holding 1000: only one commits."""
    w = boot(
        fixture(users=[user("bob", 0), user("op", 1000, uid="u_op")], operators=["u_op"]),
        handles=("bob", "op"),
    )
    payload = {"transfers": [{"from_handle": "op", "to_handle": "bob", "amount": 600}]}

    def one(i):
        c = api()
        return c.post("/settlements", json=payload,
                      headers={"Idempotency-Key": new_key()})

    results = race(one, 2)
    for r in results:
        assert_no_5xx(r)
    codes = [r.status_code for r in results]
    assert codes.count(201) == 1, f"settlements overspent: {codes}"
    assert codes.count(409) == 1, codes
    for r in results:
        if r.status_code == 409:
            assert_error(r, 409, "insufficient_funds")
    assert w.op.balance() == 400
    assert w.bob.balance() == 600
    assert w.op.balance() + w.bob.balance() == w.total


def test_many_payments_are_conserved_and_never_negative(boot, api):
    """A burst of varied simultaneous payments keeps the ledger exact."""
    w = boot(fixture(users=[user("ada", 5000), user("bob", 5000)]),
             handles=("ada", "bob"))

    def one(i):
        c = api()
        src, dst = ("ada", "bob") if i % 2 == 0 else ("bob", "ada")
        amount = 1 + (i * 37) % 97
        owner = w.ada if src == "ada" else w.bob
        return owner.post(PAY, json={"to_handle": dst, "amount": amount},
                          headers={"Idempotency-Key": new_key()})

    results = race(one, 60)
    for r in results:
        assert_no_5xx(r)
        assert r.status_code in (201, 409), r.text
    assert w.ada.balance() >= 0
    assert w.bob.balance() >= 0
    assert w.ada.balance() + w.bob.balance() == w.total


def test_fifty_inflight_reads_never_5xx(world, api):
    """Reads under the published 50-in-flight limit stay healthy."""
    def one(i):
        c = api()
        return c.get("/me")

    results = race(one, 50)
    assert all(r.status_code == 200 for r in results), \
        [r.status_code for r in results if r.status_code != 200]
