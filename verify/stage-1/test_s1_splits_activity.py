"""S1-C17 S1-C18 S1-C28: splits, activity feed, scope smoke."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c17_split_shares_and_requests(world):
    body = assert_status(
        world.ada.post(
            "/splits",
            json={"amount": 1000, "participant_handles": ["ada", "bob", "cy"], "note": "dinner"},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert [s["amount"] for s in body["shares"]] == fx.equal_split(1000, 3)
    assert [r["payer_handle"] for r in body["requests"]] == ["bob", "cy"]
    assert sum(s["amount"] for s in body["shares"]) == 1000


@pytest.mark.parametrize(
    "amount,n,expected",
    [(1000, 3, [334, 333, 333]), (1, 3, [1, 0, 0]), (10, 3, [4, 3, 3])],
)
def test_s1_c17_split_rounding_table(reset, api, amount, n, expected):
    handles = ["a", "b", "c"][:n]
    users = [fx.user(h, 1000, uid=f"u_{h}") for h in handles]
    reset(fx.fixture(users=users))
    caller = api().authenticate(users[0]["email"], users[0]["password"])
    body = assert_status(
        caller.post(
            "/splits",
            json={"amount": amount, "participant_handles": handles},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    assert [s["amount"] for s in body["shares"]] == expected


def test_s1_c18_activity_visibility(world, pay):
    """S1-U9: cy keeps the public ada→bob payment after a later private one."""
    pub = assert_status(pay(world.ada, to_handle="bob", amount=100, visibility="public"), 201).json()
    assert len(world.cy.get("/activity").json()["payments"]) == 1
    priv = assert_status(pay(world.ada, to_handle="bob", amount=50, visibility="private"), 201).json()
    cy_feed = world.cy.get("/activity").json()["payments"]
    assert len(cy_feed) == 1, "third party sees public only, not the private payment"
    assert cy_feed[0]["payment_id"] == pub["payment_id"]
    assert cy_feed[0]["visibility"] == "public" and cy_feed[0]["amount"] == 100
    ada_feed = world.ada.get("/activity").json()["payments"]
    assert len(ada_feed) == 2
    assert len(world.bob.get("/activity").json()["payments"]) == 2
    by_id = {p["payment_id"]: p for p in ada_feed}
    assert by_id[pub["payment_id"]]["visibility"] == "public"
    assert by_id[priv["payment_id"]]["visibility"] == "private"


def test_s1_c18_requests_never_in_activity(world, ask):
    assert_status(ask(amount=100), 201)
    assert world.ada.get("/activity").json()["payments"] == []


def test_s1_c18_activity_pagination(world, pay):
    for _ in range(3):
        assert_status(pay(amount=1), 201)
    page = world.ada.get("/activity", params={"limit": 2, "offset": 0}).json()
    assert len(page["payments"]) == 2
    assert page["has_more"] is True


def test_s1_c28_scope_endpoints_exist(world, ask, pay):
    assert_status(world.ada.get("/me"), 200)
    assert_status(pay(amount=1), 201)
    assert_status(ask(amount=1), 201)
    assert_status(
        world.ada.post(
            "/splits", json={"amount": 3, "participant_handles": ["ada", "bob"]}, idempotency_key=new_key()
        ),
        201,
    )
    assert_status(world.ada.get("/activity"), 200)
    assert_status(world.ada.get("/requests"), 200)
