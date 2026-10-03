"""Pytest fixtures for Pocketful Stage 1 verifier suite."""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import httpx
import pytest

ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib import fixtures as fx  # noqa: E402
from lib.http import Api, RESET_TIMEOUT, assert_status, new_key  # noqa: E402


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("BASE_URL")
    if not url:
        pytest.fail("BASE_URL environment variable is required (set by scripts/lever.py boot/checks)")
    return url.rstrip("/")


@pytest.fixture
def reset(base_url):
    def _reset(fixture: dict, *, raw: bool = False) -> httpx.Response:
        resp = httpx.post(f"{base_url}/_test/reset", json=fixture, timeout=RESET_TIMEOUT)
        if not raw:
            assert_status(resp, 204)
        return resp

    return _reset


@pytest.fixture
def api(base_url):
    made: list[Api] = []

    def _api(token: str | None = None) -> Api:
        client = Api(base_url, token=token)
        made.append(client)
        return client

    yield _api
    for client in made:
        client.close()


@pytest.fixture
def world(reset, api):
    fixture = fx.fixture()
    reset(fixture)
    return SimpleNamespace(
        fixture=fixture,
        total=fx.seeded_total(fixture),
        currency=fixture["currency"],
        minor_units=fixture["minor_units"],
        ada=api().authenticate(fx.ADA["email"], fx.ADA["password"]),
        bob=api().authenticate(fx.BOB["email"], fx.BOB["password"]),
        cy=api().authenticate(fx.CY["email"], fx.CY["password"]),
    )


@pytest.fixture
def balance():
    def _balance(client: Api) -> int:
        resp = client.get("/me")
        assert resp.status_code == 200, resp.text
        return resp.json()["balance"]

    return _balance


@pytest.fixture
def conservation(balance):
    def _check(world_, clients=None):
        clients = clients or [world_.ada, world_.bob, world_.cy]
        total = sum(balance(c) for c in clients)
        assert total == world_.total, f"money was created or destroyed: {total} != seeded {world_.total}"
        return total

    return _check


@pytest.fixture
def pay(world):
    def _pay(client=None, *, to_handle="bob", amount=100, key=None, **extra):
        body = {"to_handle": to_handle, "amount": amount}
        body.update(extra)
        return (client or world.ada).post(
            "/payments", json=body, idempotency_key=new_key() if key is None else key
        )

    return _pay


@pytest.fixture
def ask(world):
    def _ask(client=None, *, payer_handle="ada", amount=1200, key=None, **extra):
        body = {"payer_handle": payer_handle, "amount": amount}
        body.update(extra)
        return (client or world.bob).post(
            "/requests", json=body, idempotency_key=new_key() if key is None else key
        )

    return _ask
