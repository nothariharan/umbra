"""S1-C20 S1-C27: error envelope and no-5xx under concurrent load."""
from __future__ import annotations

import httpx
import pytest

from lib import fixtures as fx
from lib.concurrent import burst, no_5xx, tally
from lib.http import Api, assert_error, error_code, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c20_error_envelope_shape(world, pay):
    resp = pay(to_handle="ada")
    assert resp.status_code == 422
    code = error_code(resp)
    assert code == "self_payment"
    body = resp.json()
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]


def test_s1_c27_burst_payments_no_5xx(reset, base_url):
    reset(fx.fixture(users=[fx.user("ada", 1000), fx.user("bob", 0)]))
    clients = [Api(base_url).authenticate("ada@example.com", "correct horse") for _ in range(10)]
    try:
        out = burst(
            lambda i: clients[i].post(
                "/payments", json={"to_handle": "bob", "amount": 1000}, idempotency_key=new_key()
            ),
            10,
        )
        no_5xx(out)
        counts = tally(out)
        assert counts.get(201, 0) + counts.get(409, 0) == 10
    finally:
        for c in clients:
            c.close()


def test_s1_c27_many_parallel_reads_no_5xx(world):
    def read(_i):
        return world.ada.get("/me")

    no_5xx(burst(read, 50))
