"""§6–§11 edge cases from spec part 2 (idempotency, splits, settlements, auth)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.concurrent import burst, no_5xx, tally
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c22_concurrent_identical_idempotency_one_201(world, conservation):
    key = new_key()
    body = {"to_handle": "bob", "amount": 50}

    def shoot(_i):
        return world.ada.post("/payments", json=body, idempotency_key=key)

    out = burst(shoot, 10)
    no_5xx(out)
    counts = tally(out)
    assert counts.get(201) == 1, counts
    assert counts.get(200) == 9, counts
    conservation(world)


def test_s1_c22_idempotency_scoped_per_user(world, pay):
    key = "same-key-string-for-two-users"
    assert_status(pay(world.ada, amount=10, key=key), 201)
    assert_status(
        world.bob.post(
            "/payments",
            json={"to_handle": "cy", "amount": 10},
            idempotency_key=key,
        ),
        201,
    )


def test_s1_c22_claimed_key_before_field_validation(world, pay):
    key = new_key()
    assert_status(pay(amount=10, key=key), 201)
    assert_error(
        world.ada.post("/payments", json={"to_handle": "bob", "amount": 0}, idempotency_key=key),
        409,
        "idempotency_key_reuse",
    )


def test_s1_c14_pay_body_empty_vs_public_are_distinct(world, ask):
    rq = assert_status(ask(amount=40), 201).json()["request_id"]
    key = new_key()
    assert_status(world.ada.post(f"/requests/{rq}/pay", json={}, idempotency_key=key), 201)
    rq2 = assert_status(ask(amount=41), 201).json()["request_id"]
    assert_error(
        world.ada.post(
            f"/requests/{rq2}/pay",
            json={"visibility": "public"},
            idempotency_key=key,
        ),
        409,
        "idempotency_key_reuse",
    )


def test_s1_c22_idempotent_paths_requests_splits_settlements(world, ask, reset, api):
    key_r = new_key()
    rq = assert_status(ask(amount=5, key=key_r), 201).json()
    assert_status(ask(amount=5, key=key_r), 200).json() == rq

    key_s = new_key()
    split = assert_status(
        world.ada.post(
            "/splits",
            json={"amount": 6, "participant_handles": ["ada", "bob"]},
            idempotency_key=key_s,
        ),
        201,
    ).json()
    assert world.ada.post(
        "/splits",
        json={"amount": 6, "participant_handles": ["ada", "bob"]},
        idempotency_key=key_s,
    ).json() == split

    fixture = fx.fixture(settlement_operator_ids=[fx.ADA["id"]])
    reset(fixture)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    key_t = new_key()
    batch = {
        "transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 1}],
    }
    first = assert_status(ada.post("/settlements", json=batch, idempotency_key=key_t), 201).json()
    replay = assert_status(ada.post("/settlements", json=batch, idempotency_key=key_t), 200).json()
    assert replay == first


def test_s1_c17_split_caller_only_and_zero_share_request(world, reset, api):
    reset(fx.fixture())
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    solo = assert_status(
        ada.post(
            "/splits",
            json={"amount": 100, "participant_handles": ["ada"]},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert solo["requests"] == []
    assert solo["shares"] == [{"handle": "ada", "amount": 100}]

    split = assert_status(
        ada.post(
            "/splits",
            json={"amount": 1, "participant_handles": ["ada", "bob", "cy"]},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert [s["amount"] for s in split["shares"]] == [1, 0, 0]
    zero_req = next(r for r in split["requests"] if r["payer_handle"] == "cy")
    assert zero_req["amount"] == 0 and zero_req["status"] == "pending"


def test_s1_c24_settlement_collective_insufficient_funds_unchanged(reset, api):
    fixture = fx.fixture(settlement_operator_ids=[fx.ADA["id"]])
    reset(fixture)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    before = ada.get("/me").json()["balance"]
    assert_error(
        ada.post(
            "/settlements",
            json={
                "transfers": [
                    {"from_handle": "ada", "to_handle": "bob", "amount": 2000},
                    {"from_handle": "bob", "to_handle": "cy", "amount": 5000},
                ]
            },
            idempotency_key=new_key(),
        ),
        409,
        "insufficient_funds",
    )
    assert ada.get("/me").json()["balance"] == before


def test_s1_c9_multiple_login_tokens_both_valid(world, api):
    t1 = assert_status(world.ada.login(fx.ADA["email"], fx.ADA["password"]), 200).json()["token"]
    t2 = assert_status(world.ada.login(fx.ADA["email"], fx.ADA["password"]), 200).json()["token"]
    assert t1 and t2
    assert_status(api(t1).get("/me"), 200)
    assert_status(api(t2).get("/me"), 200)


def test_s1_c25_operator_cannot_see_others_private_activity_or_requests(reset, api, pay):
    fixture = fx.fixture(settlement_operator_ids=[fx.CY["id"]])
    reset(fixture)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    bob = api().authenticate(fx.BOB["email"], fx.BOB["password"])
    cy = api().authenticate(fx.CY["email"], fx.CY["password"])
    assert_status(
        ada.post(
            "/payments",
            json={"to_handle": "bob", "amount": 10, "visibility": "private"},
            idempotency_key=new_key(),
        ),
        201,
    )
    assert cy.get("/activity").json()["payments"] == []
    assert_status(
        bob.post("/requests", json={"payer_handle": "ada", "amount": 5}, idempotency_key=new_key()),
        201,
    )
    assert cy.get("/requests").json()["requests"] == []


def test_s1_c12_note_longer_than_200_rejected(world, pay):
    assert_error(pay(note="x" * 201), 422, "validation_failed")


def test_s1_c16_unknown_direction_or_status_422(world):
    assert_error(world.ada.get("/requests", params={"direction": "sideways"}), 422, "validation_failed")
    assert_error(world.ada.get("/requests", params={"status": "open"}), 422, "validation_failed")


def test_s1_c23_import_preserves_idempotency_replay(world, pay, reset):
    key = new_key()
    receipt = assert_status(pay(amount=33, key=key), 201).json()
    snap = world.ada.get("/_test/export", token=None).json()
    reset(world.fixture)
    assert_status(world.ada.post("/_test/import", json=snap, token=None), 204)
    replay = assert_status(
        world.ada.post(
            "/payments",
            json={"to_handle": "bob", "amount": 33},
            idempotency_key=key,
        ),
        200,
    ).json()
    assert replay == receipt
