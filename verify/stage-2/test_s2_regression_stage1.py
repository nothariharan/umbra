"""S2-C26: stage-1 behaviour unchanged when no holds (S2-R1, deltas from part 2)."""
from __future__ import annotations

import pytest

from s2lib.http import assert_status, new_key

pytestmark = pytest.mark.stage(2)


def test_s2_c26_stage1_pay_and_activity_unchanged_without_holds(world, pay, conservation):
    assert_status(pay(amount=100, visibility="public"), 201)
    assert_status(pay(client=world.bob, to_handle="ada", amount=50), 201)
    feed = world.cy.get("/activity").json()
    payments = feed.get("payments", feed)
    assert len(payments) >= 1
    conservation(world)


def test_s2_c26_request_pay_uses_available_when_no_holds(world, me_wallet):
    from s2lib.http import new_key as nk

    rq = assert_status(
        world.bob.post(
            "/requests",
            json={"payer_handle": "ada", "amount": 100},
            idempotency_key=nk(),
        ),
        201,
    ).json()
    avail_before = me_wallet(world.ada)["available"]
    assert_status(
        world.ada.post(f"/requests/{rq['request_id']}/pay", idempotency_key=nk()),
        201,
    )
    assert me_wallet(world.ada)["available"] == avail_before - 100
