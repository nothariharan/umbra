"""S3-C14..S3-C19: revisions, corrections, activity/revision reads."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(3)


def _seed_payment(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "public",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    return "pay1"


def test_s3_c14_revision_one_fields(reset, world):
    pid = _seed_payment(reset, world)
    revs = assert_status(world.ada.get(f"/payments/{pid}/revisions"), 200).json()["revisions"]
    assert revs[0]["revision"] == 1
    assert revs[0]["amount"] == 500
    assert revs[0]["reason"] == ""
    assert revs[0]["effective_at"] == revs[0]["recorded_at"] == "2026-09-20T12:00:00+00:00"


def test_s3_c15_opening_balance_unchanged_after_correction(reset, world, me_wallet):
    pid = _seed_payment(reset, world)
    opening = me_wallet(world.ada, as_of="2026-09-19T00:00:00+00:00")["balance"]
    body = {
        "expected_revision": 1,
        "amount": 400,
        "effective_at": "2026-09-20T12:00:00+00:00",
        "reason": "fix amount",
    }
    assert_status(
        world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=new_key()),
        201,
    )
    assert me_wallet(world.ada, as_of="2026-09-19T00:00:00+00:00")["balance"] == opening


def test_s3_c16_correction_validation_and_forbidden(reset, world, pay):
    pid = _seed_payment(reset, world)
    assert_error(
        world.bob.post(
            f"/payments/{pid}/corrections",
            json={
                "expected_revision": 1,
                "amount": 1,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "x",
            },
            idempotency_key=new_key(),
        ),
        403,
        "forbidden",
    )
    assert_error(
        world.ada.post(
            "/payments/missing/corrections",
            json={
                "expected_revision": 1,
                "amount": 1,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "x",
            },
            idempotency_key=new_key(),
        ),
        404,
        "not_found",
    )


def test_s3_c17_insufficient_funds_on_increase(reset, world, me_wallet):
    pid = _seed_payment(reset, world)
    avail = me_wallet(world.ada)["available"]
    body = {
        "expected_revision": 1,
        "amount": 500 + avail + 1,
        "effective_at": "2026-09-20T12:00:00+00:00",
        "reason": "too big",
    }
    assert_error(
        world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=new_key()),
        409,
        "insufficient_funds",
    )


def test_s3_c18_idempotency_and_stale_revision(reset, world):
    pid = _seed_payment(reset, world)
    body = {
        "expected_revision": 1,
        "amount": 450,
        "effective_at": "2026-09-20T12:00:00+00:00",
        "reason": "adjust",
    }
    key = new_key()
    first = assert_status(
        world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=key),
        201,
    )
    replay = assert_status(
        world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=key),
        200,
    )
    assert replay.json()["revision"] == first.json()["revision"]
    assert_error(
        world.ada.post(
            f"/payments/{pid}/corrections",
            json={**body, "expected_revision": 1},
            idempotency_key=new_key(),
        ),
        409,
        "stale_revision",
    )


def test_s3_c19_activity_original_only_revisions_party_read(reset, world):
    pid = _seed_payment(reset, world)
    body = {
        "expected_revision": 1,
        "amount": 300,
        "effective_at": "2026-09-20T12:00:00+00:00",
        "reason": "adjust",
    }
    assert_status(
        world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=new_key()),
        201,
    )
    act = assert_status(world.ada.get("/activity"), 200).json()["payments"]
    assert len(act) == 1 and act[0]["amount"] == 500
    assert_status(world.ada.get(f"/payments/{pid}/revisions"), 200)
    assert_error(world.cy.get(f"/payments/{pid}/revisions"), 404, "not_found")
