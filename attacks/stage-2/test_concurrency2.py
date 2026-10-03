"""Stage 2 — concurrency of holds, captures and correctness under races.

S2-R30 (concurrent requests equivalent to a serial order, invariants at every read),
S2-R17/R18/R19 (total, available, capture invariants).
"""
from __future__ import annotations

from attacklib2 import (
    assert_status,
    fixture2,
    new_key,
    race,
    s1_user,
)


def wallet(client) -> dict:
    body = client.me_full()
    for field in ("balance", "total", "available", "held"):
        assert field in body, f"GET /me must expose {field!r}. got {sorted(body)}"
    return body


def count(client) -> int:
    resp = assert_status(client.get("/activity"), 200)
    body = resp.json()
    items = body.get("payments", body) if isinstance(body, dict) else body
    return len(items)


def test_concurrent_full_captures_move_money_exactly_once(world, conservation):
    aid = assert_status(world.ada.authorize("bob", 1_000), 201).json()["authorization_id"]
    n = 24

    def attempt(_i):
        return world.bob.capture(aid, 1_000, key=new_key())

    results = race(attempt, n)
    created = [r for r in results if r.status_code == 201]
    assert all(r.status_code < 500 for r in results), \
        f"5xx under concurrent capture: {[r.status_code for r in results]}"
    assert len(created) == 1, \
        f"exactly one capture may succeed, got {[r.status_code for r in results]}"

    ada, bob = wallet(world.ada), wallet(world.bob)
    assert ada["held"] == 0
    assert ada["total"] == 99_000 and bob["total"] == 1_500, "capture moved money once"
    assert count(world.ada) == 1, "one payment, not one per request"
    conservation()


def test_concurrent_partial_captures_never_exceed_authorized(world, conservation):
    total = 1_000
    step = 100
    aid = assert_status(world.ada.authorize("bob", total), 201).json()["authorization_id"]
    n = 30

    def attempt(_i):
        return world.bob.capture(aid, step, final=False, key=new_key())

    results = race(attempt, n)
    assert all(r.status_code < 500 for r in results), \
        f"5xx under concurrent capture: {[r.status_code for r in results]}"
    ok = [r for r in results if r.status_code == 201]
    captured = step * len(ok)
    assert captured <= total, f"cumulative captures {captured} exceeded authorized {total}"

    item = world.ada.find_authorization(aid)
    assert item["captured_amount"] == captured, \
        f"captured_amount {item['captured_amount']} != successful captures {captured}"
    assert item["remaining_amount"] == total - captured >= 0
    ada = wallet(world.ada)
    assert ada["held"] == total - captured
    # a capture moves money and releases the same hold, so available is unchanged
    assert ada["total"] == 100_000 - captured
    assert ada["available"] == 99_000
    conservation()


def test_concurrent_authorizations_cannot_overspend_available(boot, conservation):
    ns = boot(fixture2(users=[s1_user("ada", 1_000), s1_user("bob", 0),
                              s1_user("cy", 0)]), handles=("ada", "bob", "cy"))
    n = 40

    def attempt(_i):
        return ns.ada.authorize("bob", 100, key=new_key())

    results = race(attempt, n)
    assert all(r.status_code < 500 for r in results), \
        f"5xx under concurrent authorize: {[r.status_code for r in results]}"
    ok = [r for r in results if r.status_code == 201]
    assert len(ok) <= 10, f"holds {len(ok) * 100} exceeded total 1000"
    ada = wallet(ns.ada)
    assert ada["available"] >= 0, "available went negative"
    assert ada["held"] == 100 * len(ok)
    conservation()


def test_payment_and_authorization_race_uses_available_once(boot, conservation):
    ns = boot(fixture2(users=[s1_user("ada", 1_000), s1_user("bob", 0),
                              s1_user("cy", 0)]), handles=("ada", "bob", "cy"))

    def pay(_i):
        return ns.ada.post("/payments", json={"to_handle": "bob", "amount": 600},
                           headers={"Idempotency-Key": new_key()})

    def hold(_i):
        return ns.ada.authorize("cy", 600, key=new_key())

    results = race(lambda i: pay(i) if i == 0 else hold(i), 2)
    assert all(r.status_code < 500 for r in results)
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409], f"exactly one of payment/hold may win: {codes}"
    ada = wallet(ns.ada)
    assert ada["available"] >= 0
    payment_won = any(r.status_code == 201 and r.request.url.path == "/payments"
                      for r in results)
    if payment_won:
        assert (ada["total"], ada["held"], ada["available"]) == (400, 0, 400)
    else:
        assert (ada["total"], ada["held"], ada["available"]) == (1_000, 600, 400)
    conservation()


def test_capture_and_void_race_is_serialisable(world, conservation):
    aid = assert_status(world.ada.authorize("bob", 1_000), 201).json()["authorization_id"]

    def capture(_i):
        return world.bob.capture(aid, 1_000, key=new_key())

    def void(_i):
        return world.ada.void(aid)

    results = race(lambda i: capture(i) if i == 0 else void(i), 2)
    assert all(r.status_code < 500 for r in results)

    item = world.ada.find_authorization(aid)
    ada, bob = wallet(world.ada), wallet(world.bob)
    if item["status"] == "captured":
        assert count(world.ada) == 1, "a captured authorization must have its payment"
        assert bob["total"] == 1_500, "capture moved money"
        assert ada["held"] == 0
    elif item["status"] == "voided":
        assert count(world.ada) == 0, "a voided authorization must not move money"
        assert bob["total"] == 500, "void must leave the receiver untouched"
        assert ada["held"] == 0
    else:
        raise AssertionError(f"capture/void race left status {item['status']!r}")
    conservation()


def test_conservation_under_mixed_concurrent_writes(world):
    """Many overlapping payments, holds and captures: total is invariant throughout."""
    for round_no in range(3):
        aid_box: list[str] = []

        def op(i):
            if i % 3 == 0:
                return world.ada.post("/payments", json={"to_handle": "bob", "amount": 10},
                                      headers={"Idempotency-Key": new_key()})
            if i % 3 == 1:
                return world.ada.authorize("cy", 20, key=new_key())
            resp = world.ada.authorize("bob", 30, key=new_key())
            if resp.status_code == 201:
                aid_box.append(resp.json()["authorization_id"])
            return resp

        results = race(op, 12)
        assert all(r.status_code < 500 for r in results), \
            f"5xx in round {round_no}: {[r.status_code for r in results]}"
        # invariants at every read
        total = 0
        for c in world.all:
            w = wallet(c)
            assert w["available"] >= 0, "available negative under load"
            assert w["held"] >= 0
            total += w["total"]
        assert total == world.total, f"round {round_no}: total {total} != {world.total}"
        # capture every hold that landed, which must also preserve conservation
        for aid in aid_box:
            world.bob.capture(aid, body={}, key=new_key())
        total = sum(wallet(c)["total"] for c in world.all)
        assert total == world.total, f"round {round_no} after capture: {total}"
