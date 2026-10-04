"""Part 2/2 spec refinements: batch precedence, replay, snapshots, offset-normalized effective times."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import Api, assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(4)

EFFECTIVE = "2026-09-20T12:00:00+00:00"


def _operator(reset, api):
    reset(fx.fixture(settlement_operator_ids=[fx.ADA["id"]]))
    return api().authenticate(fx.ADA["email"], fx.ADA["password"])


def test_s4_batch_precedence_item_404_before_incomplete_settlement(reset, api):
    ada = _operator(reset, api)
    reset(
        fx.fixture(
            settlement_operator_ids=[fx.ADA["id"]],
            payments=[
                {
                    "id": "s_a",
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 100,
                    "visibility": "private",
                    "settlement_id": "set1",
                    "created_at": EFFECTIVE,
                },
                {
                    "id": "s_b",
                    "from_user_id": fx.BOB["id"],
                    "to_user_id": fx.CY["id"],
                    "amount": 100,
                    "visibility": "private",
                    "settlement_id": "set1",
                    "created_at": EFFECTIVE,
                },
            ],
        )
    )
    assert_error(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": "missing",
                        "expected_revision": 1,
                        "amount": 1,
                        "effective_at": EFFECTIVE,
                        "reason": "first",
                    },
                    {
                        "payment_id": "s_a",
                        "expected_revision": 1,
                        "amount": 90,
                        "effective_at": EFFECTIVE,
                        "reason": "partial set",
                    },
                ]
            },
            idempotency_key=new_key(),
        ),
        404,
        "not_found",
    )


def test_s4_batch_settlement_same_instant_different_offset_spelling(reset, api):
    ada = _operator(reset, api)
    reset(
        fx.fixture(
            settlement_operator_ids=[fx.ADA["id"]],
            payments=[
                {
                    "id": "s_a",
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 100,
                    "visibility": "private",
                    "settlement_id": "set1",
                    "created_at": EFFECTIVE,
                },
                {
                    "id": "s_b",
                    "from_user_id": fx.BOB["id"],
                    "to_user_id": fx.CY["id"],
                    "amount": 100,
                    "visibility": "private",
                    "settlement_id": "set1",
                    "created_at": EFFECTIVE,
                },
            ],
        )
    )
    assert_status(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": "s_a",
                        "expected_revision": 1,
                        "amount": 90,
                        "effective_at": EFFECTIVE,
                        "reason": "a",
                    },
                    {
                        "payment_id": "s_b",
                        "expected_revision": 1,
                        "amount": 90,
                        "effective_at": "2026-09-20T12:00:00Z",
                        "reason": "b",
                    },
                ]
            },
            idempotency_key=new_key(),
        ),
        201,
    )


def test_s4_batch_recorded_at_strictly_after_member_prior(reset, api):
    ada = _operator(reset, api)
    reset(
        fx.fixture(
            settlement_operator_ids=[fx.ADA["id"]],
            payments=[
                {
                    "id": "p1",
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 200,
                    "visibility": "public",
                    "created_at": EFFECTIVE,
                }
            ],
        )
    )
    rev1 = assert_status(ada.get("/payments/p1/revisions"), 200).json()["revisions"][0]
    batch = assert_status(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": "p1",
                        "expected_revision": 1,
                        "amount": 150,
                        "effective_at": EFFECTIVE,
                        "reason": "batch",
                    }
                ]
            },
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert batch["recorded_at"] > rev1["recorded_at"]


def test_s4_batch_snapshot_frozen_and_statement_updates(reset, api):
    ada = _operator(reset, api)
    reset(
        fx.fixture(
            settlement_operator_ids=[fx.ADA["id"]],
            payments=[
                {
                    "id": "p1",
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 300,
                    "visibility": "public",
                    "created_at": EFFECTIVE,
                }
            ],
        )
    )
    before = assert_status(ada.get("/statement"), 200).json()
    token = before["snapshot"]
    frozen = assert_status(
        ada.get("/statement", params={"snapshot": token, "limit": 50, "offset": 0}),
        200,
    ).json()
    assert_status(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": "p1",
                        "expected_revision": 1,
                        "amount": 250,
                        "effective_at": EFFECTIVE,
                        "reason": "batch",
                    }
                ]
            },
            idempotency_key=new_key(),
        ),
        201,
    )
    after_snap = assert_status(
        ada.get("/statement", params={"snapshot": token, "limit": 50, "offset": 0}),
        200,
    ).json()
    assert after_snap["entries"] == frozen["entries"]
    after = assert_status(ada.get("/statement"), 200).json()
    assert after["entries"][-1]["payment"]["amount"] == 250


def test_s4_batch_does_not_mutate_idempotent_payment_replay(reset, api):
    ada = _operator(reset, api)
    reset(fx.fixture(settlement_operator_ids=[fx.ADA["id"]]))
    key = new_key()
    pay = assert_status(
        ada.post("/payments", json={"to_handle": "bob", "amount": 88}, idempotency_key=key),
        201,
    ).json()
    pid = pay["payment_id"]
    assert_status(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": pid,
                        "expected_revision": 1,
                        "amount": 80,
                        "effective_at": EFFECTIVE,
                        "reason": "batch",
                    }
                ]
            },
            idempotency_key=new_key(),
        ),
        201,
    )
    replay = assert_status(
        ada.post("/payments", json={"to_handle": "bob", "amount": 88}, idempotency_key=key),
        200,
    ).json()
    assert replay["payment_id"] == pay["payment_id"]
    assert replay["amount"] == pay["amount"]


def test_s4_correction_batches_unauthenticated_401(base_url):
    anon = Api(base_url, token=None)
    try:
        assert anon.post(
            "/correction-batches",
            json={"corrections": []},
            idempotency_key=new_key(),
        ).status_code == 401
    finally:
        anon.close()
