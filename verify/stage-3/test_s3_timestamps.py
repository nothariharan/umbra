"""S3-C2..S3-C5: payment timestamps and seeded history."""
from __future__ import annotations

import re

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status

pytestmark = pytest.mark.stage(3)

RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")


def test_s3_c2_created_at_on_payment_endpoints(world, pay, me_wallet):
    resp = pay(amount=120)
    assert_status(resp, 201)
    body = resp.json()
    assert RFC3339.match(body["created_at"]), body["created_at"]
    act = world.ada.get("/activity")
    assert_status(act, 200)
    items = act.json()["payments"]
    assert items and RFC3339.match(items[0]["created_at"])


def test_s3_c3_activity_ordered_by_created_at(world, reset, pay):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "p_old",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 10,
                "visibility": "public",
                "created_at": "2026-09-20T10:00:00+00:00",
            },
            {
                "id": "p_new",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 20,
                "visibility": "public",
                "created_at": "2026-09-21T10:00:00+00:00",
            },
        ]
    )
    reset(fx_body)
    act = world.ada.get("/activity")
    assert_status(act, 200)
    ids = [p["payment_id"] for p in act.json()["payments"]]
    # S3-U3: activity newest-first (descending created_at), same as stages 1–2.
    assert ids.index("p_new") < ids.index("p_old")


def test_s3_c4_future_seeded_created_at_rejected(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "p_bad",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 1,
                "visibility": "public",
                "created_at": "2099-01-01T00:00:00+00:00",
            }
        ]
    )
    resp = reset(fx_body, raw=True)
    assert_error(resp, 422, "validation_failed")


def test_s3_c5_seeded_payments_preserve_balances(reset, world, me_wallet):
    fx_body = fx.fixture(
        users=[fx.ADA, fx.BOB, fx.CY],
        payments=[
            {
                "id": "p1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "public",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ],
    )
    reset(fx_body)
    assert me_wallet(world.ada)["balance"] == fx.ADA["balance"]
    assert me_wallet(world.bob)["balance"] == fx.BOB["balance"]
