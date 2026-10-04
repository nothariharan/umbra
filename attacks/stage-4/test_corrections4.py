"""S4-R11, R12: stage-3 single-correction scope under stage-4 refunds."""
from __future__ import annotations

from attacklib4 import (
    assert_error,
    assert_status,
    authz,
    fixture3,
    future_iso,
    new_key,
)

PASSWORD = "correct horse"


def _users(ada=1000, bob=1000, cy=1000, op=1000):
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


def _direct(world, amount=100):
    return assert_status(world.ada.post(
        "/payments", json={"to_handle": "bob", "amount": amount},
        headers={"Idempotency-Key": new_key()}), 201).json()


def _corr(made, amount, rev=1, reason="x"):
    return {"expected_revision": rev, "amount": amount,
            "effective_at": made["created_at"], "reason": reason}


def test_ordinary_direct_and_request_stay_correctable(world4):
    direct = _direct(world4, 100)
    assert_status(world4.ada.correct(direct["payment_id"], _corr(direct, 140)), 201)
    req = assert_status(world4.bob.post(
        "/requests", json={"payer_handle": "ada", "amount": 50},
        headers={"Idempotency-Key": new_key()}), 201).json()
    pay = assert_status(world4.ada.post(
        f"/requests/{req['request_id']}/pay", json={},
        headers={"Idempotency-Key": new_key()}), 201).json()
    assert_status(world4.ada.correct(pay["payment_id"], _corr(pay, 80)), 201)


def test_capture_and_refund_payments_are_immutable(world4):
    authorized = assert_status(world4.ada.authorize("bob", 80), 201).json()
    cap = assert_status(world4.bob.capture(authorized["authorization_id"], amount=80), 201).json()
    assert_error(world4.ada.correct(cap["payment_id"], _corr(cap, 40)),
                 422, "linked_payment_immutable")

    direct = _direct(world4, 100)
    refund = assert_status(world4.bob.refund(direct["payment_id"], 40), 201).json()
    # the refund's sender is bob; try both parties to be sure it is immutable for all
    assert_error(world4.bob.correct(refund["payment_id"], _corr(refund, 20)),
                 422, "linked_payment_immutable")
    assert_error(world4.ada.correct(refund["payment_id"], _corr(refund, 20)),
                 403, "forbidden")


def test_settlement_member_single_correction_stays_immutable(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 100}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    member = settled["payments"][0]
    assert_error(world.ada.correct(member["payment_id"], _corr(member, 50)),
                 422, "linked_payment_immutable")


def test_correction_cannot_drop_below_refunded_amount(world4):
    made = _direct(world4, 100)
    pid = made["payment_id"]
    assert_status(world4.bob.refund(pid, 60), 201)
    assert_error(world4.ada.correct(pid, _corr(made, 50)), 422, "refund_exceeds_payment")
    # at or above the refunded sum is allowed
    assert_status(world4.ada.correct(pid, _corr(made, 60)), 201)


def test_correction_debit_respects_available_funds(boot4):
    # ada has exactly enough for the original payment, none for an increase
    world = boot4(fixture3(users=_users(ada=100, bob=0, cy=0, op=0), operators=[]))
    made = _direct(world, 100)
    assert world.ada.me_full()["available"] == 0
    before = world.ada.me_full()
    assert_error(world.ada.correct(made["payment_id"], _corr(made, 150)),
                 409, "insufficient_funds")
    assert world.ada.me_full() == before, "a failed correction must not move money"
