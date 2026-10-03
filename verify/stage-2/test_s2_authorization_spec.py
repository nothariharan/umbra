"""S2-C19, S2-C22, S2-C23: authorization API spec from stage-2 part 2 (S2-R21-R27)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from s2lib import fixtures as fx
from s2lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(2)


def test_s2_c22_fixture_rejects_holds_exceeding_balance(reset):
    ada = dict(fx.ADA)
    bob = dict(fx.BOB)
    body = fx.fixture(users=[ada, bob])
    body["authorizations"] = [
        {
            "id": "a_bad",
            "from_user_id": ada["id"],
            "to_user_id": bob["id"],
            "amount": ada["balance"] + 1,
            "note": "",
            "visibility": "public",
            "status": "open",
            "expires_at": "2099-06-01T00:00:00+00:00",
        }
    ]
    resp = reset(body, raw=True)
    assert_error(resp, 422, "validation_failed")


def test_s2_c22_ttl_default_on_create(world, authorize):
    auth = assert_status(authorize(amount=100), 201).json()
    created = datetime.fromisoformat(auth["created_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(auth["expires_at"].replace("Z", "+00:00"))
    delta = (expires - created).total_seconds()
    assert 590 <= delta <= 610


def test_s2_c23_expired_seed_releases_available_on_read(reset, api, me_wallet):
    ada = dict(fx.ADA)
    bob = dict(fx.BOB)
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(timespec="seconds")
    body = fx.fixture(users=[ada, bob])
    body["authorizations"] = [
        {
            "id": "a_exp",
            "from_user_id": ada["id"],
            "to_user_id": bob["id"],
            "amount": 3000,
            "note": "",
            "visibility": "public",
            "status": "open",
            "expires_at": past,
        }
    ]
    reset(body)
    client = api().authenticate(ada["email"], ada["password"])
    me = me_wallet(client)
    assert me["held"] == 0
    assert me["available"] == me["total"]
    listed = client.get("/authorizations", params={"status": "expired"}).json()
    items = listed.get("authorizations", listed)
    assert any(a.get("id") == "a_exp" or a.get("authorization_id") == "a_exp" for a in items)


def test_s2_c19_extended_capture_final_false(world, authorize, me_wallet):
    auth = assert_status(authorize(amount=2000), 201).json()
    aid = auth["authorization_id"]
    cap1 = world.bob.post(
        f"/authorizations/{aid}/capture",
        json={"amount": 700, "final": False},
        idempotency_key=new_key(),
    )
    assert_status(cap1, 201)
    row = world.ada.get(f"/authorizations").json()
    items = row.get("authorizations", row)
    current = next(x for x in items if x.get("authorization_id") == aid or x.get("id") == aid)
    assert current["status"] == "open"
    assert current.get("remaining_amount", 2000 - 700) == 1300
    me = me_wallet(world.ada)
    assert me["held"] == 1300


def test_s2_c19_final_capture_releases_remainder(world, authorize, me_wallet):
    auth = assert_status(authorize(amount=2000), 201).json()
    aid = auth["authorization_id"]
    before = me_wallet(world.ada)
    assert_status(
        world.bob.post(
            f"/authorizations/{aid}/capture",
            json={"amount": 1500},
            idempotency_key=new_key(),
        ),
        201,
    )
    after = me_wallet(world.ada)
    assert after["held"] == 0
    assert after["available"] == after["balance"] == before["balance"] - 1500
    assert after["available"] == before["available"] + (2000 - 1500)


def test_s2_c19_second_capture_after_final_is_not_open(world, authorize):
    auth = assert_status(authorize(amount=500), 201).json()
    aid = auth["authorization_id"]
    assert_status(
        world.bob.post(f"/authorizations/{aid}/capture", json={}, idempotency_key=new_key()),
        201,
    )
    again = world.bob.post(
        f"/authorizations/{aid}/capture",
        json={},
        idempotency_key=new_key(),
    )
    assert_error(again, 409, "authorization_not_open")


@pytest.mark.parametrize("bad_amount", [0, -1, 1.5, "x"])
def test_s2_c19_capture_invalid_amount_validation_failed(world, authorize, bad_amount):
    auth = assert_status(authorize(amount=500), 201).json()
    aid = auth["authorization_id"]
    resp = world.bob.post(
        f"/authorizations/{aid}/capture",
        json={"amount": bad_amount},
        idempotency_key=new_key(),
    )
    assert_error(resp, 422, "validation_failed")


def test_s2_c19_capture_exceeds_remainder(world, authorize):
    auth = assert_status(authorize(amount=400), 201).json()
    aid = auth["authorization_id"]
    resp = world.bob.post(
        f"/authorizations/{aid}/capture",
        json={"amount": 401},
        idempotency_key=new_key(),
    )
    assert_error(resp, 422, "capture_exceeds_authorization")


def test_s2_c19_capture_idempotency_body_must_match(world, authorize):
    auth = assert_status(authorize(amount=800), 201).json()
    aid = auth["authorization_id"]
    key = new_key()
    first = world.bob.post(f"/authorizations/{aid}/capture", json={"amount": 800}, idempotency_key=key)
    assert_status(first, 201)
    reuse = world.bob.post(f"/authorizations/{aid}/capture", json={}, idempotency_key=key)
    assert_error(reuse, 409, "idempotency_key_reuse")


def test_s2_c19_capture_replay_identical_body(world, authorize):
    auth = assert_status(authorize(amount=600), 201).json()
    aid = auth["authorization_id"]
    key = new_key()
    body = {"amount": 600}
    r1 = world.bob.post(f"/authorizations/{aid}/capture", json=body, idempotency_key=key)
    r2 = world.bob.post(f"/authorizations/{aid}/capture", json=body, idempotency_key=key)
    assert_status(r1, 201)
    assert_status(r2, 200)
    assert r1.json()["payment_id"] == r2.json()["payment_id"]


def test_s2_c20_void_idempotent_and_not_open_when_captured(world, authorize):
    auth = assert_status(authorize(amount=500), 201).json()
    aid = auth["authorization_id"]
    assert_status(world.bob.post(f"/authorizations/{aid}/capture", json={}, idempotency_key=new_key()), 201)
    bad = world.ada.post(f"/authorizations/{aid}/void")
    assert_error(bad, 409, "authorization_not_open")
    open_auth = assert_status(authorize(amount=300), 201).json()
    oid = open_auth["authorization_id"]
    v1 = assert_status(world.ada.post(f"/authorizations/{oid}/void"), 200)
    v2 = assert_status(world.ada.post(f"/authorizations/{oid}/void"), 200)
    assert v1.json()["status"] == v2.json()["status"] == "voided"


def test_s2_c18_create_validation_and_not_found(world):
    assert_error(
        world.ada.post(
            "/authorizations",
            json={"to_handle": "ada", "amount": 10},
            idempotency_key=new_key(),
        ),
        422,
        "self_payment",
    )
    assert_error(
        world.ada.post(
            "/authorizations",
            json={"to_handle": "missing_user", "amount": 10},
            idempotency_key=new_key(),
        ),
        404,
        "not_found",
    )


def test_s2_c17_payment_immediate_no_hold(world, pay, me_wallet):
    before = me_wallet(world.ada)
    assert_status(pay(amount=50), 201)
    after = me_wallet(world.ada)
    assert after["held"] == before["held"]
    assert after["balance"] == before["balance"] - 50
    body = assert_status(pay(amount=25), 201).json()
    assert body.get("authorization_id") in (None, "")


def test_s2_c19_capture_expired_authorization(reset, api, authorize):
    ada = dict(fx.ADA)
    bob = dict(fx.BOB)
    body = fx.fixture(users=[ada, bob], authorization_ttl_seconds=1)
    reset(body)
    client = api().authenticate(ada["email"], ada["password"])
    auth = assert_status(
        client.post(
            "/authorizations",
            json={"to_handle": "bob", "amount": 100},
            idempotency_key=new_key(),
        ),
        201,
    ).json()
    aid = auth["authorization_id"]
    import time

    time.sleep(1.2)
    bob = api().authenticate(bob["email"], bob["password"])
    resp = bob.post(f"/authorizations/{aid}/capture", json={}, idempotency_key=new_key())
    assert_error(resp, 409, "authorization_expired")
