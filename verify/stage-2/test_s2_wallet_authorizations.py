"""S2-C16..S2-C22: /me, authorizations, capture, void, list (S2-R17-R25)."""
from __future__ import annotations

import pytest

from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(2)


def test_s2_c16_me_balance_total_available(world, me_wallet):
    me = me_wallet(world.ada)
    assert me["balance"] == me["total"]
    assert me["available"] == me["total"] - me["held"]
    assert me["held"] == 0


def test_s2_c18_create_authorization_holds_available(world, me_wallet, authorize):
    before = me_wallet(world.ada)
    resp = authorize(amount=2000)
    assert_status(resp, 201)
    after = me_wallet(world.ada)
    assert after["balance"] == before["balance"]
    assert after["held"] == before["held"] + 2000
    assert after["available"] == before["available"] - 2000


def test_s2_c18_authorization_not_in_activity(world, authorize):
    resp = authorize(amount=100)
    assert_status(resp, 201)
    feed = world.cy.get("/activity").json()
    ids = {p.get("payment_id") for p in feed.get("payments", feed) if isinstance(feed, dict)}
    assert resp.json()["authorization_id"] not in {str(x) for x in ids}


def test_s2_c19_capture_creates_payment(world, authorize, me_wallet):
    auth = assert_status(authorize(amount=1500), 201).json()
    cap = world.bob.post(
        f"/authorizations/{auth['authorization_id']}/capture",
        json={"amount": 700},
        idempotency_key=new_key(),
    )
    assert_status(cap, 201)
    pay = cap.json()
    assert pay.get("authorization_id") == auth["authorization_id"]
    assert pay["amount"] == 700
    me = me_wallet(world.ada)
    assert me["held"] == 1500 - 700 or me["held"] == 800  # remainder still held until final


def test_s2_c20_void_releases_hold(world, authorize, me_wallet):
    auth = assert_status(authorize(amount=900), 201).json()
    mid = me_wallet(world.ada)
    assert mid["held"] >= 900
    void = world.ada.post(f"/authorizations/{auth['authorization_id']}/void")
    assert_status(void, 200)
    after = me_wallet(world.ada)
    assert after["held"] == mid["held"] - 900


def test_s2_c21_list_filters_direction(world, authorize):
    assert_status(authorize(amount=100), 201)
    out = world.ada.get("/authorizations", params={"direction": "outgoing"}).json()
    inc = world.bob.get("/authorizations", params={"direction": "incoming"}).json()
    out_items = out.get("authorizations", out)
    inc_items = inc.get("authorizations", inc)
    assert len(out_items) >= 1
    assert len(inc_items) >= 1


def test_s2_c20_capture_errors_forbidden(world, authorize):
    auth = assert_status(authorize(amount=500), 201).json()
    resp = world.ada.post(
        f"/authorizations/{auth['authorization_id']}/capture",
        json={},
        idempotency_key=new_key(),
    )
    assert_error(resp, 403, "forbidden")


def test_s2_c18_insufficient_on_available_not_total(reset, api, me_wallet):
    from lib import fixtures as fxmod

    ada = dict(fxmod.ADA)
    ada["balance"] = 1000
    bob = dict(fxmod.BOB)
    body = fxmod.fixture(users=[ada, bob, fxmod.CY])
    body["authorizations"] = [
        {
            "id": "a_seed",
            "from_user_id": ada["id"],
            "to_user_id": bob["id"],
            "amount": 900,
            "note": "",
            "visibility": "public",
            "status": "open",
            "expires_at": "2099-01-01T00:00:00+00:00",
        }
    ]
    reset(body)
    client = api().authenticate(ada["email"], ada["password"])
    me = me_wallet(client)
    assert me["available"] <= 100
    resp = client.post("/payments", json={"to_handle": "bob", "amount": 200}, idempotency_key=new_key())
    assert_error(resp, 409, "insufficient_funds")
