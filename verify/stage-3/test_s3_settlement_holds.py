"""S3-C24..S3-C28: settlements, import, holds, statement vs lifecycle."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(3)


def test_s3_c24_settlement_member_immutable(reset, world):
    fx_body = fx.fixture(
        settlement_operator_ids=[fx.ADA["id"]],
        payments=[
            {
                "id": "settle_p",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 100,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
                "settlement_id": "s1",
            }
        ],
    )
    reset(fx_body)
    assert_error(
        world.ada.post(
            "/payments/settle_p/corrections",
            json={
                "expected_revision": 1,
                "amount": 90,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "nope",
            },
            idempotency_key=new_key(),
        ),
        422,
        "linked_payment_immutable",
    )


def test_s3_c25_capture_linked_payment_immutable(reset, world, authorize):
    fx_body = fx.fixture()
    reset(fx_body)
    auth = assert_status(authorize(amount=200), 201).json()
    cap = assert_status(
        world.bob.post(
            f"/authorizations/{auth['authorization_id']}/capture",
            json={},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    pid = cap["payment_id"]
    assert_error(
        world.ada.post(
            f"/payments/{pid}/corrections",
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


def test_s3_c26_historical_me_hold_fields(reset, world, authorize, me_wallet):
    fx_body = fx.fixture()
    reset(fx_body)
    assert_status(authorize(amount=300), 201)
    as_of = "2026-09-24T14:00:00+00:00"
    me = me_wallet(world.ada, as_of=as_of, known_at=as_of)
    assert me["balance"] == me["total"]
    assert me["available"] == me["total"] - me["held"]


def test_s3_c27_closed_at_on_authorization(reset, world, authorize):
    fx_body = fx.fixture()
    reset(fx_body)
    auth = assert_status(authorize(amount=100), 201).json()
    listed = assert_status(world.ada.get("/authorizations"), 200).json()["authorizations"]
    row = next(a for a in listed if a["authorization_id"] == auth["authorization_id"])
    assert row.get("closed_at") in (None, "")


def test_s3_c28_statement_payments_only_no_auth_rows(reset, world, authorize):
    fx_body = fx.fixture()
    reset(fx_body)
    auth = assert_status(authorize(amount=150), 201).json()
    assert_status(
        world.bob.post(
            f"/authorizations/{auth['authorization_id']}/capture",
            json={},
            idempotency_key=new_key(),
        ),
        201,
    )
    st = assert_status(world.ada.get("/statement"), 200).json()
    assert len(st["entries"]) >= 1
    assert all("payment" in e and "delta" in e for e in st["entries"])
