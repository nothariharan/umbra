"""S4-R2..S4-R10: refunds."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(4)


def _seed_direct(reset, amount=500):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": amount,
                "visibility": "public",
                "note": "dinner",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    return "pay1"


def test_s4_c2_refund_requires_idempotency_and_amount(reset, world, refund):
    pid = _seed_direct(reset)
    assert_error(
        world.bob.post(f"/payments/{pid}/refunds", json={"amount": 100}),
        400,
        "missing_idempotency_key",
    )
    assert_error(
        world.bob.post(
            f"/payments/{pid}/refunds",
            json={},
            idempotency_key=new_key(),
        ),
        422,
        "validation_failed",
    )


def test_s4_c3_refund_receiver_only_and_unknown_payment(reset, world, refund):
    pid = _seed_direct(reset)
    assert_error(refund(world.ada, pid, 50), 403, "forbidden")
    assert_error(refund(world.bob, "missing", 50), 404, "not_found")


def test_s4_c4_refund_target_rules_and_refund_of_refund(reset, world, refund, pay):
    pid = _seed_direct(reset)
    first = assert_status(refund(world.bob, pid, 100), 201).json()
    assert first.get("refund_of") == pid
    assert_error(refund(world.ada, first["payment_id"], 50), 422, "invalid_refund_target")


def test_s4_c5_refund_invalid_amount(reset, world, refund):
    pid = _seed_direct(reset)
    assert_error(refund(world.bob, pid, -1), 422, "validation_failed")
    assert_error(refund(world.bob, pid, 0), 422, "validation_failed")


def test_s4_c6_refund_exceeds_corrected_payment(reset, world, refund):
    pid = _seed_direct(reset, amount=200)
    assert_status(refund(world.bob, pid, 150), 201)
    assert_error(refund(world.bob, pid, 100), 422, "refund_exceeds_payment")


def test_s4_c7_refund_payment_shape_and_non_refund_null_refund_of(reset, world, refund, pay):
    pid = _seed_direct(reset)
    body = assert_status(refund(world.bob, pid, 120), 201).json()
    assert body["from_user_id"] == fx.BOB["id"]
    assert body["to_user_id"] == fx.ADA["id"]
    assert body["amount"] == 120
    assert body["refund_of"] == pid
    assert body["request_id"] is None
    assert body["authorization_id"] is None
    assert body["note"] == "dinner"
    assert body["visibility"] == "public"
    other = assert_status(pay(amount=50), 201).json()
    assert other.get("refund_of") is None


def test_s4_c8_refund_idempotent_replay(reset, world, refund):
    pid = _seed_direct(reset)
    key = new_key()
    first = assert_status(refund(world.bob, pid, 80, key=key), 201)
    second = assert_status(refund(world.bob, pid, 80, key=key), 200)
    assert second.json() == first.json()


def test_s4_c9_refund_insufficient_available_funds(reset, world, refund, api):
    fx_body = fx.fixture(
        users=[fx.ADA, fx.user("bob", 0), fx.CY],
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": "u_bob",
                "amount": 500,
                "visibility": "public",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ],
    )
    reset(fx_body)
    bob = api().authenticate("bob@example.com", "correct horse")
    assert_error(refund(bob, "pay1", 100), 409, "insufficient_funds")


def test_s4_c10_refund_does_not_reopen_request_or_hold(reset, world, refund, authorize):
    fx_body = fx.fixture(
        requests=[
            {
                "id": "req1",
                "requester_id": fx.BOB["id"],
                "payer_id": fx.ADA["id"],
                "amount": 300,
                "note": "x",
                "status": "paid",
                "payment_id": "pay_req",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ],
        payments=[
            {
                "id": "pay_req",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 300,
                "visibility": "public",
                "request_id": "req1",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ],
    )
    reset(fx_body)
    assert_status(refund(world.bob, "pay_req", 100), 201)
    reqs = assert_status(world.bob.get("/requests"), 200).json()["requests"]
    paid = next(r for r in reqs if r["request_id"] == "req1")
    assert paid["status"] == "paid"
    assert paid["payment_id"] == "pay_req"

    reset(fx.fixture())
    auth = assert_status(authorize(amount=400), 201).json()
    cap = assert_status(
        world.bob.post(
            f"/authorizations/{auth['authorization_id']}/capture",
            json={},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    held_before = assert_status(world.ada.get("/me"), 200).json()["held"]
    assert_status(refund(world.bob, cap["payment_id"], 50), 201)
    held_after = assert_status(world.ada.get("/me"), 200).json()["held"]
    assert held_after == held_before
