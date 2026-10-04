"""S3-C20..S3-C23: known_at views and snapshot pagination."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(3)


def test_s3_c20_known_at_echo_and_selection(reset, world, me_wallet):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    k = "2026-09-20T11:00:00+00:00"
    me = me_wallet(world.ada, known_at=k)
    assert me.get("known_at") == k
    st = assert_status(world.ada.get("/statement", params={"known_at": k}), 200).json()
    assert st.get("known_at") == k


def test_s3_c21_corrected_statement_order(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    assert_status(
        world.ada.post(
            "/payments/pay1/corrections",
            json={
                "expected_revision": 1,
                "amount": 0,
                "effective_at": "2026-09-19T12:00:00+00:00",
                "reason": "zero out",
            },
            idempotency_key=new_key(),
        ),
        201,
    )
    st = assert_status(
        world.ada.get("/statement", params={"known_at": "2026-09-21T00:00:00+00:00"}),
        200,
    ).json()
    if st["entries"]:
        entry = st["entries"][0]
        assert entry["payment"]["amount"] == 0
        assert entry["delta"] == 0


def test_s3_c22_snapshot_token_paging(reset, world):
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
            for i in range(3)
        ]
    )
    reset(fx_body)
    first = assert_status(world.ada.get("/statement"), 200).json()
    token = first.get("snapshot")
    assert token
    page = assert_status(world.ada.get("/statement", params={"snapshot": token, "limit": 1}), 200).json()
    assert page["opening_balance"] == first["opening_balance"]
    assert_error(
        world.ada.get("/statement", params={"snapshot": token, "from": "2026-09-20T00:00:00+00:00"}),
        422,
        "validation_failed",
    )


def test_s3_c23_snapshot_stable_under_writes(reset, world, pay):
    fx_body = fx.fixture()
    reset(fx_body)
    snap_resp = assert_status(world.ada.get("/statement"), 200).json()
    token = snap_resp["snapshot"]
    assert_status(pay(amount=25), 201)
    frozen = assert_status(world.ada.get("/statement", params={"snapshot": token}), 200).json()
    assert frozen["entries"] == snap_resp["entries"]
