"""S3-R2..R5: payment timestamps, activity ordering, seeded times, seeded balances."""
from __future__ import annotations

import datetime as _dt

from attacklib3 import (
    assert_status,
    entries_of,
    fixture3,
    new_key,
    parse_ts,
    payment_seed,
    plus,
)


def _feed(c, order_desc=True):
    resp = assert_status(c.get("/activity"), 200)
    return resp.json()["payments"]


def test_payment_created_at_rfc3339_on_every_reader(world3):
    made = assert_status(
        world3.ada.post("/payments", json={"to_handle": "bob", "amount": 100},
                        headers={"Idempotency-Key": new_key()}), 201).json()
    pid = made["payment_id"]
    made_ts = parse_ts(made["created_at"])

    feed = {p["payment_id"]: p for p in _feed(world3.ada)}
    assert pid in feed, "the new payment must appear in the sender's activity"
    assert parse_ts(feed[pid]["created_at"]) == made_ts

    statement = assert_status(world3.ada.statement(limit=200), 200)
    entries = {e["payment"]["payment_id"]: e for e in entries_of(statement)}
    assert pid in entries, "the payment must appear in the sender's statement"
    assert parse_ts(entries[pid]["payment"]["created_at"]) == made_ts


def test_seeded_created_at_orders_activity_newest_first(boot3):
    t1 = "2026-09-24T08:00:00+00:00"
    t2 = "2026-09-24T09:00:00+00:00"
    world = boot3(fixture3(payments=[
        payment_seed("p_old", "u_ada", "u_bob", 100, created_at=t1),
        payment_seed("p_new", "u_bob", "u_ada", 100, created_at=t2),
    ]))
    order = [p["payment_id"] for p in _feed(world.ada)]
    assert order == ["p_new", "p_old"], \
        f"activity must stay newest-first by created_at, got {order}"


def test_seeded_omission_uses_reset_time_before_api_payments(boot3):
    world = boot3(fixture3(payments=[
        payment_seed("p_seeded", "u_bob", "u_ada", 10),
    ]))
    made = assert_status(
        world.ada.post("/payments", json={"to_handle": "bob", "amount": 20},
                       headers={"Idempotency-Key": new_key()}), 201).json()
    order = [p["payment_id"] for p in _feed(world.ada)]
    assert order and order[0] == made["payment_id"], \
        f"a reset-time seeded payment must sort before later API payments, got {order}"
    seeded = next(p for p in _feed(world.ada) if p["payment_id"] == "p_seeded")
    assert parse_ts(seeded["created_at"]) <= parse_ts(made["created_at"])


def test_future_seeded_created_at_is_422_and_changes_nothing(api, boot3, reset):
    world = boot3(fixture3())
    before = world.ada.me_full()
    future = plus(3600)
    resp = reset(fixture3(payments=[
        payment_seed("p_future", "u_ada", "u_bob", 100, created_at=future),
    ]), expect=None)
    assert resp.status_code == 422, f"future created_at must be 422, got {resp.status_code}"
    assert resp.json().get("error", {}).get("code") == "validation_failed", resp.text

    after = assert_status(world.ada.get("/me"), 200).json()
    assert after["balance"] == before["balance"], "a rejected reset must not change state"
    assert after.get("total") == before.get("total")


def test_seeded_payments_do_not_change_fixture_balance(boot3):
    base = fixture3(users=[
        {"id": "u_ada", "email": "ada@example.com", "password": "correct horse",
         "display_name": "Ada", "handle": "ada", "balance": 1000},
        {"id": "u_bob", "email": "bob@example.com", "password": "correct horse",
         "display_name": "Bob", "handle": "bob", "balance": 0},
    ], operators=[], payments=[
        payment_seed("p_seed", "u_ada", "u_bob", 400, created_at="2026-09-24T08:00:00+00:00"),
    ])
    world = boot3(base)
    assert world.ada.me_full()["balance"] == 1000, \
        "loading seeded payments must not change the fixture balance"
    assert world.bob.me_full()["balance"] == 0
    total = sum(c.me_full()["balance"] for c in world.all)
    assert total == world.total


def test_invalid_seeded_created_at_forms_are_422(reset):
    for bad in ("2026-09-24T08:00:00", "2026-09-24", "", "not-a-time"):
        resp = reset(fixture3(payments=[
            payment_seed("p_bad", "u_ada", "u_bob", 100, created_at=bad),
        ]), expect=None)
        assert resp.status_code == 422, f"created_at {bad!r} must be 422, got {resp.status_code}"
        assert resp.json().get("error", {}).get("code") == "validation_failed", resp.text


def test_activity_orders_by_instant_not_by_string(boot3):
    # C is earliest (02:30Z), A is 06:00Z, B is 09:00Z; lexicographically A < C < B.
    a = payment_seed("p_a", "u_ada", "u_bob", 100, created_at="2026-09-24T06:00:00+00:00")
    b = payment_seed("p_b", "u_bob", "u_ada", 100, created_at="2026-09-24T11:00:00+02:00")
    c = payment_seed("p_c", "u_bob", "u_ada", 100, created_at="2026-09-24T08:00:00+05:30")
    world = boot3(fixture3(payments=[a, b, c]))
    order = [p["payment_id"] for p in _feed(world.ada)]
    assert order == ["p_b", "p_a", "p_c"], (
        "activity must order by the instant, not the literal offset string; "
        f"got {order}")
