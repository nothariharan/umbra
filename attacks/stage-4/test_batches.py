"""S4-R13..R16, R19: batch auth, body bounds, per-item errors and operator scope."""
from __future__ import annotations

from attacklib4 import (
    assert_error,
    assert_status,
    batch_item,
    fixture3,
    new_key,
    new_s4_client,
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


def _payer(payer, to_handle, amount):
    return assert_status(payer.post(
        "/payments", json={"to_handle": to_handle, "amount": amount},
        headers={"Idempotency-Key": new_key()}), 201).json()


def _batch_of(mades, amount=0):
    return [batch_item(m["payment_id"], 1, amount, m["created_at"]) for m in mades]


def test_batch_requires_operator_and_idempotency(world4):
    made = _payer(world4.ada, "bob", 100)
    items = _batch_of([made])
    anon = new_s4_client(token=None)
    try:
        # 401 for a missing token (any 401 body is acceptable, but it must not be 2xx)
        assert anon.batch(items, key_sent=False).status_code == 401
    finally:
        anon.close()
    # 403 for an authenticated non-operator
    assert_error(world4.ada.batch(items), 403, "forbidden")
    # missing key for the operator -> 400
    assert_error(world4.op.batch(items, key_sent=False), 400, "missing_idempotency_key")


def test_batch_body_bounds_and_distinct_ids(world4):
    mades = [_payer(world4.ada, "bob", 1) for _ in range(33)]
    assert_error(world4.op.batch([]), 422, "validation_failed")
    assert_error(world4.op.batch(_batch_of(mades[:33])), 422, "validation_failed")
    dup = _batch_of([mades[0], mades[0]])
    assert_error(world4.op.batch(dup), 422, "validation_failed")
    # 1 and 32 are inside the boundary
    assert_status(world4.op.batch(_batch_of(mades[:1])), 201)
    mades2 = [_payer(world4.ada, "bob", 1) for _ in range(32)]
    assert_status(world4.op.batch(_batch_of(mades2)), 201)


def test_batch_per_item_unknown_and_stale(world4):
    made = _payer(world4.ada, "bob", 100)
    unknown = batch_item("p_missing", 1, 50, made["created_at"])
    assert_error(world4.op.batch([unknown]), 404, "not_found")
    stale = batch_item(made["payment_id"], 99, 50, made["created_at"])
    assert_error(world4.op.batch([stale]), 409, "stale_revision")


def test_batch_scope_ordinary_request_settlement_ok_captures_refunds_immutable(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    ordinary = _payer(world.ada, "bob", 100)
    assert_status(world.op.batch(_batch_of([ordinary], amount=120)), 201)

    req = assert_status(world.bob.post(
        "/requests", json={"payer_handle": "ada", "amount": 50},
        headers={"Idempotency-Key": new_key()}), 201).json()
    req_pay = assert_status(world.ada.post(
        f"/requests/{req['request_id']}/pay", json={},
        headers={"Idempotency-Key": new_key()}), 201).json()
    assert_status(world.op.batch(_batch_of([req_pay], amount=70)), 201)

    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 30}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    assert_status(world.op.batch(_batch_of([settled["payments"][0]], amount=20)), 201)

    authorized = assert_status(world.ada.authorize("bob", 40), 201).json()
    cap = assert_status(world.bob.capture(authorized["authorization_id"], amount=40), 201).json()
    assert_error(world.op.batch(_batch_of([cap], amount=10)), 422, "linked_payment_immutable")

    direct = _payer(world.ada, "bob", 100)
    ref = assert_status(world.bob.refund(direct["payment_id"], 40), 201).json()
    assert_error(world.op.batch(_batch_of([ref], amount=10)), 422, "linked_payment_immutable")


def test_batch_ignores_unknown_top_level_fields(world4):
    made = _payer(world4.ada, "bob", 100)
    resp = world4.op.batch(_batch_of([made], amount=0),
                           extra={"surprise": "ignored", "nested": {"a": 1}})
    assert resp.status_code == 201, f"unknown top-level fields must be ignored: {resp.text}"


def test_successful_batch_does_not_poison_later_created_at(world4):
    first = _payer(world4.ada, "bob", 100)
    assert_status(world4.op.batch(_batch_of([first], amount=90)), 201)
    later = _payer(world4.ada, "bob", 1)
    created = later["created_at"]
    resp = world4.op.batch([batch_item(later["payment_id"], 1, 0, created)])
    assert resp.status_code == 201, (
        "after a successful batch, a payment the service just created must accept its own "
        f"created_at as effective_at, got {resp.status_code} {resp.text} (created_at={created})")
