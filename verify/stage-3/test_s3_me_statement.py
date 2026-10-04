"""S3-C6..S3-C13, S3-C21: temporal /me and baseline statements."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status
from s3lib.stage3_model import model_from_fixture

pytestmark = pytest.mark.stage(3)


def test_s3_c6_invalid_as_of_validation_failed(world, me_wallet):
    assert_error(world.ada.get("/me", params={"as_of": "2026-09-24"}), 422, "validation_failed")
    assert_error(world.ada.get("/me", params={"as_of": ""}), 422, "validation_failed")


def test_s3_c7_as_of_balance_edges(reset, world, me_wallet):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "p1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 400,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    model = model_from_fixture(fx_body)
    before = "2026-09-19T00:00:00+00:00"
    at = "2026-09-20T12:00:00+00:00"
    after = "2026-09-21T00:00:00+00:00"
    me_before = me_wallet(world.ada, as_of=before)
    me_at = me_wallet(world.ada, as_of=at)
    me_after = me_wallet(world.ada, as_of=after)
    assert me_before["balance"] == model.opening_balance(fx.ADA["id"])
    assert me_at["balance"] == model.balance_at(fx.ADA["id"], model.ledger["p1"].created_at)
    assert me_after["balance"] == me_at["balance"]


def test_s3_c8_as_of_echo(world, me_wallet):
    q = "2026-09-24T13:20:00+00:00"
    body = me_wallet(world.ada, as_of=q)
    assert body.get("as_of") == q


def test_s3_c9_statement_defaults_and_window(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "p1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 100,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    st = world.ada.get("/statement")
    assert_status(st, 200)
    data = st.json()
    assert "opening_balance" in data and "entries" in data and "closing_balance" in data


def test_s3_c10_statement_entry_shape(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "p1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 250,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    st = world.ada.get(
        "/statement",
        params={"from": "2026-09-20T00:00:00+00:00", "to": "2026-09-21T00:00:00+00:00"},
    )
    data = assert_status(st, 200).json()
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["delta"] == -250
    assert entry["payment"]["payment_id"] == "p1"
    assert "balance_after" in entry


def test_s3_c11_statement_balances_reconcile(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "p1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 100,
                "visibility": "private",
                "created_at": "2026-09-20T10:00:00+00:00",
            },
            {
                "id": "p2",
                "from_user_id": fx.BOB["id"],
                "to_user_id": fx.ADA["id"],
                "amount": 40,
                "visibility": "private",
                "created_at": "2026-09-20T11:00:00+00:00",
            },
        ]
    )
    reset(fx_body)
    params = {"from": "2026-09-20T00:00:00+00:00", "to": "2026-09-21T00:00:00+00:00"}
    full = assert_status(world.ada.get("/statement", params=params), 200).json()
    opening = full["opening_balance"]
    closing = full["closing_balance"]
    assert opening + sum(e["delta"] for e in full["entries"]) == closing


def test_s3_c12_pagination_preserves_balances(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": f"p{i}",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 10 + i,
                "visibility": "private",
                "created_at": f"2026-09-20T{10+i:02d}:00:00+00:00",
            }
            for i in range(4)
        ]
    )
    reset(fx_body)
    params = {"from": "2026-09-20T00:00:00+00:00", "to": "2026-09-21T00:00:00+00:00"}
    full = assert_status(world.ada.get("/statement", params=params), 200).json()
    page = assert_status(world.ada.get("/statement", params={**params, "limit": 2, "offset": 1}), 200).json()
    assert page["opening_balance"] == full["opening_balance"]
    assert page["closing_balance"] == full["closing_balance"]
    assert page["entries"][0]["balance_after"] == full["entries"][1]["balance_after"]


def test_s3_c13_statement_party_visibility_not_activity(reset, world, pay):
    fx_body = fx.fixture()
    reset(fx_body)
    assert_status(pay(to_handle="bob", amount=50, visibility="private"), 201)
    st_ada = assert_status(world.ada.get("/statement"), 200).json()
    st_cy = assert_status(world.cy.get("/statement"), 200).json()
    assert len(st_ada["entries"]) >= 1
    assert st_cy["entries"] == []
