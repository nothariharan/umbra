"""S1-C24 S1-C25: operator settlements."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c24_operator_settlement_atomic(reset, api, conservation):
    fixture = fx.fixture(settlement_operator_ids=[fx.ADA["id"]])
    reset(fixture)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    resp = assert_status(
        ada.post(
            "/settlements",
            json={
                "transfers": [
                    {"from_handle": "ada", "to_handle": "bob", "amount": 100},
                    {"from_handle": "bob", "to_handle": "cy", "amount": 50},
                ]
            },
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert resp["settlement_id"] and resp["committed_at"]
    assert len(resp["payments"]) == 2
    assert resp["payments"][0]["settlement_id"] == resp["settlement_id"]
    bob = api().authenticate(fx.BOB["email"], fx.BOB["password"])
    cy = api().authenticate(fx.CY["email"], fx.CY["password"])
    total = sum(c.get("/me").json()["balance"] for c in (ada, bob, cy))
    assert total == fx.seeded_total(fixture)


def test_s1_c24_settlement_errors(reset, api):
    fixture = fx.fixture(settlement_operator_ids=[fx.ADA["id"]])
    reset(fixture)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    assert_error(
        ada.post(
            "/settlements",
            json={"transfers": [{"from_handle": "ada", "to_handle": "missing_x", "amount": 1}]},
            idempotency_key=new_key(),
        ),
        404,
        "not_found",
    )
    assert_error(
        ada.post(
            "/settlements",
            json={"transfers": [{"from_handle": "ada", "to_handle": "ada", "amount": 1}]},
            idempotency_key=new_key(),
        ),
        422,
        "self_payment",
    )


def test_s1_c25_non_operator_forbidden(world):
    assert_error(
        world.bob.post(
            "/settlements",
            json={"transfers": [{"from_handle": "bob", "to_handle": "cy", "amount": 1}]},
            idempotency_key=new_key(),
        ),
        403,
        "forbidden",
    )
