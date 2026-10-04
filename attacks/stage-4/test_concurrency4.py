"""S4-R25: concurrent writers sharing an expected revision cannot both commit."""
from __future__ import annotations

from attacklib4 import (
    assert_status,
    batch_item,
    fixture3,
    new_key,
    race,
)

PASSWORD = "correct horse"


def _users(ada=100000, bob=1000, cy=1000, op=100000):
    return [
        {"id": "u_ada", "email": "ada@example.com", "password": PASSWORD,
         "display_name": "Ada", "handle": "ada", "balance": ada},
        {"id": "u_bob", "email": "bob@example.com", "password": PASSWORD,
         "display_name": "Bob", "handle": "bob", "balance": bob},
        {"id": "u_cy", "email": "cy@example.com", "password": PASSWORD,
         "display_name": "Cy", "handle": "cy", "balance": cy},
        {"id": "u_op", "email": "op@example.com", "password": PASSWORD,
         "display_name": "Op", "handle": "op", "balance": op},
    ]


def _world(boot4, ada=100000):
    return boot4(fixture3(users=_users(ada=ada), operators=["u_op"]))


def _pay(world, to_handle="bob", amount=100):
    return assert_status(world.ada.post(
        "/payments", json={"to_handle": to_handle, "amount": amount},
        headers={"Idempotency-Key": new_key()}), 201).json()


def test_concurrent_single_corrections_same_revision_one_wins(boot4):
    world = _world(boot4)
    a = _pay(world)
    keys = [new_key(), new_key()]
    amounts = [130, 160]

    def attempt(i):
        return world.ada.correct(a["payment_id"], {
            "expected_revision": 1, "amount": amounts[i],
            "effective_at": a["created_at"], "reason": f"c{i}"}, key=keys[i])

    results = race(attempt, 2)
    codes = [r.status_code for r in results]
    assert sum(1 for c in codes if c == 201) <= 1, \
        f"two corrections sharing expected_revision must not both commit: {codes}"


def test_concurrent_batches_sharing_a_payment_one_wins(boot4):
    world = _world(boot4)
    a = _pay(world)
    b = _pay(world, "cy")
    keys = [new_key(), new_key()]

    def attempt(i):
        item = batch_item(a["payment_id"], 1, 70 + i, a["created_at"])
        return world.op.batch([item], key=keys[i])

    results = race(attempt, 2)
    codes = [r.status_code for r in results]
    assert sum(1 for c in codes if c == 201) <= 1, \
        f"two batches sharing a revision must not both commit: {codes}"


def test_concurrent_refunds_cannot_exceed_the_payment(boot4):
    world = _world(boot4)
    a = _pay(world, amount=100)
    before = sum(c.me_full()["balance"] for c in world.all)

    def attempt(i):
        return world.bob.refund(a["payment_id"], 60)

    results = race(attempt, 2)
    codes = [r.status_code for r in results]
    assert sum(1 for c in codes if c == 201) == 1, \
        f"exactly one 60 refund of a 100 payment may commit: {codes}"
    assert sum(c.me_full()["balance"] for c in world.all) == before, \
        "concurrent refunds must conserve the seeded total"
