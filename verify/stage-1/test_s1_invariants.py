"""S1-C26 S1-C29 S1-C30: monetary invariants, currency, handle rules."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.concurrent import burst, no_5xx, tally
from lib.http import Api, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c26_conservation_after_operations(world, pay, ask, conservation):
    assert_status(pay(amount=100), 201)
    assert_status(ask(amount=50), 201)
    conservation(world)


def test_s1_c26_request_paid_at_most_once(world, ask, balance):
    rq = assert_status(ask(amount=100), 201).json()
    key = new_key()
    assert_status(world.ada.post(f"/requests/{rq['request_id']}/pay", json={}, idempotency_key=key), 201)
    assert_status(world.ada.post(f"/requests/{rq['request_id']}/pay", json={}, idempotency_key=key), 200)
    assert balance(world.ada) == fx.ADA["balance"] - 100


def test_s1_c26_non_negative_under_competing_debits(reset, base_url, balance):
    reset(fx.fixture(users=[fx.user("ada", 500), fx.user("bob", 0), fx.user("cy", 0)]))
    ada = Api(base_url).authenticate("ada@example.com", "correct horse")
    try:
        out = burst(
            lambda i: ada.post(
                "/payments",
                json={"to_handle": "bob" if i % 2 == 0 else "cy", "amount": 300},
                idempotency_key=new_key(),
            ),
            20,
        )
        no_5xx(out)
        assert balance(ada) >= 0
        assert tally(out).get(409, 0) >= 1
    finally:
        ada.close()


def test_s1_c29_currency_minor_units_from_fixture(reset, api):
    for currency, minor in (("JPY", 0), ("BHD", 3)):
        reset(fx.fixture(currency=currency, minor_units=minor))
        me = api().authenticate(fx.ADA["email"], fx.ADA["password"]).get("/me").json()
        assert me["currency"] == currency
        assert me["minor_units"] == minor


def test_s1_c30_handle_immutable_after_signup(world, api):
    resp = assert_status(world.ada.signup("stable.user@example.com", "correct horse", "Stable"), 201)
    client = api(resp.json()["token"])
    h1 = client.get("/me").json()["handle"]
    assert_status(
        client.post("/payments", json={"to_handle": "bob", "amount": 1}, idempotency_key=new_key()), 201
    )
    h2 = client.get("/me").json()["handle"]
    assert h1 == h2 == fx.derive_handle("stable.user@example.com")
