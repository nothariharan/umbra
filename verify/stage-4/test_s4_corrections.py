"""S4-R11..S4-R12: stage-3 correction scope with refunds."""
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
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    return "pay1"


def test_s4_c11_capture_and_refund_payments_immutable(reset, world, pay, refund, authorize):
    pid = _seed_direct(reset)
    ref = assert_status(
        world.bob.post(
            f"/payments/{pid}/refunds",
            json={"amount": 50},
            idempotency_key=new_key(),
        ),
        201,
    ).json()["payment_id"]
    assert_error(
        world.bob.post(
            f"/payments/{ref}/corrections",
            json={
                "expected_revision": 1,
                "amount": 40,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "nope",
            },
            idempotency_key=new_key(),
        ),
        422,
        "linked_payment_immutable",
    )

    reset(fx.fixture())
    auth = assert_status(authorize(amount=200), 201).json()
    cap = assert_status(
        world.bob.post(
            f"/authorizations/{auth['authorization_id']}/capture",
            json={},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert_error(
        world.ada.post(
            f"/payments/{cap['payment_id']}/corrections",
            json={
                "expected_revision": 1,
                "amount": 1,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "nope",
            },
            idempotency_key=new_key(),
        ),
        422,
        "linked_payment_immutable",
    )


def test_s4_c12_correction_below_refunded_amount(reset, world, refund):
    pid = _seed_direct(reset, amount=500)
    assert_status(refund(world.bob, pid, 200), 201)
    assert_error(
        world.ada.post(
            f"/payments/{pid}/corrections",
            json={
                "expected_revision": 1,
                "amount": 250,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "too low",
            },
            idempotency_key=new_key(),
        ),
        422,
        "refund_exceeds_payment",
    )
