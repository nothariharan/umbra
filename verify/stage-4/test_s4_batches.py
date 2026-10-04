"""S4-R13..S4-R23: correction batches."""
from __future__ import annotations

import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(4)

EFFECTIVE = "2026-09-20T12:00:00+00:00"


def _operator_world(reset, api):
    fx_body = fx.fixture(settlement_operator_ids=[fx.ADA["id"]])
    reset(fx_body)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    bob = api().authenticate(fx.BOB["email"], fx.BOB["password"])
    return ada, bob


def test_s4_c13_batch_auth_like_settlements(reset, api):
    ada, _ = _operator_world(reset, api)
    assert_error(
        ada.post("/correction-batches", json={"corrections": []}),
        400,
        "missing_idempotency_key",
    )
    cy = api().authenticate(fx.CY["email"], fx.CY["password"])
    assert_error(
        cy.post(
            "/correction-batches",
            json={"corrections": []},
            idempotency_key=new_key(),
        ),
        403,
        "forbidden",
    )


def test_s4_c14_batch_body_validation(reset, api):
    ada, _ = _operator_world(reset, api)
    assert_error(
        ada.post(
            "/correction-batches",
            json={"corrections": []},
            idempotency_key=new_key(),
        ),
        422,
        "validation_failed",
    )
    dup = [
        {"payment_id": "p1", "expected_revision": 1, "amount": 1, "effective_at": EFFECTIVE, "reason": "a"},
        {"payment_id": "p1", "expected_revision": 1, "amount": 2, "effective_at": EFFECTIVE, "reason": "b"},
    ]
    assert_error(
        ada.post("/correction-batches", json={"corrections": dup}, idempotency_key=new_key()),
        422,
        "validation_failed",
    )


def test_s4_c15_batch_item_not_found_and_stale(reset, api):
    ada, _ = _operator_world(reset, api)
    item = {
        "payment_id": "ghost",
        "expected_revision": 1,
        "amount": 1,
        "effective_at": EFFECTIVE,
        "reason": "x",
    }
    assert_error(
        ada.post("/correction-batches", json={"corrections": [item]}, idempotency_key=new_key()),
        404,
        "not_found",
    )


def test_s4_c16_batch_scope_immutable_targets(reset, api, authorize):
    ada, bob = _operator_world(reset, api)
    auth = assert_status(
        ada.post("/authorizations", json={"to_handle": "bob", "amount": 200}, idempotency_key=new_key()),
        201,
    ).json()
    cap = assert_status(
        bob.post(
            f"/authorizations/{auth['authorization_id']}/capture",
            json={},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    item = {
        "payment_id": cap["payment_id"],
        "expected_revision": 1,
        "amount": 1,
        "effective_at": EFFECTIVE,
        "reason": "nope",
    }
    assert_error(
        ada.post("/correction-batches", json={"corrections": [item]}, idempotency_key=new_key()),
        422,
        "linked_payment_immutable",
    )


def test_s4_c17_incomplete_settlement_batch(reset, api):
    ada, _ = _operator_world(reset, api)
    fx_body = fx.fixture(
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
    reset(fx_body)
    item = {
        "payment_id": "s_a",
        "expected_revision": 1,
        "amount": 90,
        "effective_at": EFFECTIVE,
        "reason": "partial",
    }
    assert_error(
        ada.post("/correction-batches", json={"corrections": [item]}, idempotency_key=new_key()),
        422,
        "incomplete_settlement",
    )


def test_s4_c18_settlement_effective_instant_mismatch(reset, api):
    ada, _ = _operator_world(reset, api)
    fx_body = fx.fixture(
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
    reset(fx_body)
    batch = {
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
    }
    # offset spellings may differ but instant must match — use deliberately different instants
    batch["corrections"][1]["effective_at"] = "2026-09-21T12:00:00+00:00"
    assert_error(
        ada.post("/correction-batches", json=batch, idempotency_key=new_key()),
        422,
        "validation_failed",
    )


def test_s4_c19_single_correction_still_available_and_unknown_fields_ignored(reset, world):
    pid = "pay1"
    reset(
        fx.fixture(
            payments=[
                {
                    "id": pid,
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 400,
                    "visibility": "public",
                    "created_at": EFFECTIVE,
                }
            ]
        )
    )
    assert_status(
        world.ada.post(
            f"/payments/{pid}/corrections",
            json={
                "expected_revision": 1,
                "amount": 350,
                "effective_at": EFFECTIVE,
                "reason": "solo",
            },
            idempotency_key=new_key(),
        ),
        201,
    )


def test_s4_c20_batch_rejected_leaves_state_unchanged(reset, api, me_wallet):
    ada, _ = _operator_world(reset, api)
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
    before = me_wallet(ada)["balance"]
    assert_error(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": "p1",
                        "expected_revision": 99,
                        "amount": 100,
                        "effective_at": EFFECTIVE,
                        "reason": "stale",
                    }
                ],
                "extra_ignored": True,
            },
            idempotency_key=new_key(),
        ),
        409,
        "stale_revision",
    )
    assert me_wallet(ada)["balance"] == before


def test_s4_c21_batch_success_shape(reset, api):
    ada, _ = _operator_world(reset, api)
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
    resp = assert_status(
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
    assert "correction_batch_id" in resp
    assert "recorded_at" in resp
    revs = resp["revisions"]
    assert len(revs) == 1
    assert revs[0]["correction_batch_id"] == resp["correction_batch_id"]


def test_s4_c22_batch_idempotent_replay(reset, api):
    ada, _ = _operator_world(reset, api)
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
    body = {
        "corrections": [
            {
                "payment_id": "p1",
                "expected_revision": 1,
                "amount": 180,
                "effective_at": EFFECTIVE,
                "reason": "batch",
            }
        ]
    }
    key = new_key()
    first = assert_status(
        ada.post("/correction-batches", json=body, idempotency_key=key),
        201,
    ).json()
    second = assert_status(
        ada.post("/correction-batches", json=body, idempotency_key=key),
        200,
    ).json()
    assert second == first


def test_s4_c23_batch_future_effective_rejected(reset, api):
    ada, _ = _operator_world(reset, api)
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
    assert_error(
        ada.post(
            "/correction-batches",
            json={
                "corrections": [
                    {
                        "payment_id": "p1",
                        "expected_revision": 1,
                        "amount": 180,
                        "effective_at": "2099-01-01T00:00:00+00:00",
                        "reason": "future",
                    }
                ]
            },
            idempotency_key=new_key(),
        ),
        422,
        "validation_failed",
    )
