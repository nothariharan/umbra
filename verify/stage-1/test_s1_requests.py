"""S1-C13 S1-C14 S1-C15 S1-C16 S1-C19: money requests lifecycle."""
from __future__ import annotations

import pytest

from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c13_request_without_payer_balance_check(world, ask, balance):
    broke = balance(world.cy)
    assert_status(ask(world.bob, payer_handle="cy", amount=broke + 5000), 201)
    assert balance(world.cy) == broke


def test_s1_c13_self_request_rejected(world, ask):
    assert_error(ask(world.ada, payer_handle="ada"), 422, "self_request")


def test_s1_c14_pay_request_moves_money(world, ask, balance, conservation):
    rq = assert_status(ask(amount=1200), 201).json()
    before_a, before_b = balance(world.ada), balance(world.bob)
    pay = assert_status(
        world.ada.post(f"/requests/{rq['request_id']}/pay", json={}, idempotency_key=new_key()), 201
    ).json()
    assert pay["request_id"] == rq["request_id"]
    assert balance(world.ada) == before_a - 1200
    assert balance(world.bob) == before_b + 1200
    listed = world.ada.get("/requests").json()["requests"]
    paid = next(r for r in listed if r["request_id"] == rq["request_id"])
    assert paid["status"] == "paid" and paid["payment_id"] == pay["payment_id"]
    conservation(world)


def test_s1_c14_pay_replay_200_when_already_paid(world, ask):
    rq = assert_status(ask(amount=50), 201).json()
    key = new_key()
    first = assert_status(
        world.ada.post(f"/requests/{rq['request_id']}/pay", json={}, idempotency_key=key), 201
    ).json()
    replay = assert_status(
        world.ada.post(f"/requests/{rq['request_id']}/pay", json={}, idempotency_key=key), 200
    ).json()
    assert replay == first


def test_s1_c14_insufficient_funds_on_pay_unchanged(world, ask, balance):
    rq = assert_status(ask(world.bob, payer_handle="cy", amount=10_000), 201).json()
    before = balance(world.cy)
    assert_error(
        world.cy.post(f"/requests/{rq['request_id']}/pay", json={}, idempotency_key=new_key()),
        409,
        "insufficient_funds",
    )
    assert balance(world.cy) == before


def test_s1_c15_decline_and_cancel_idempotent(world, ask):
    rq = assert_status(ask(amount=100), 201).json()["request_id"]
    assert assert_status(world.ada.post(f"/requests/{rq}/decline"), 200).json()["status"] == "declined"
    assert_status(world.ada.post(f"/requests/{rq}/decline"), 200)
    rq2 = assert_status(ask(amount=100), 201).json()["request_id"]
    assert assert_status(world.bob.post(f"/requests/{rq2}/cancel"), 200).json()["status"] == "cancelled"
    assert_status(world.bob.post(f"/requests/{rq2}/cancel"), 200)


def test_s1_c15_wrong_party_forbidden(world, ask):
    rq = assert_status(ask(amount=100), 201).json()["request_id"]
    assert_error(world.bob.post(f"/requests/{rq}/decline"), 403, "forbidden")
    assert_error(world.ada.post(f"/requests/{rq}/cancel"), 403, "forbidden")


def test_s1_c16_requests_list_filters(world, ask):
    assert_status(ask(amount=100), 201)
    incoming = world.ada.get("/requests", params={"direction": "incoming"}).json()
    outgoing = world.bob.get("/requests", params={"direction": "outgoing"}).json()
    assert incoming["requests"] and outgoing["requests"]
    assert incoming["requests"][0]["payer_handle"] == "ada"
    pending = world.ada.get("/requests", params={"status": "pending"}).json()
    assert all(r["status"] == "pending" for r in pending["requests"])
    assert "has_more" in incoming


def test_s1_c16_bad_query_integers(world):
    assert_error(world.ada.get("/requests", params={"limit": "1e2"}), 422, "validation_failed")
    assert_error(world.ada.get("/requests", params={"offset": "4.0"}), 422, "validation_failed")
