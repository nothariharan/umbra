"""Pytest fixtures for the stage-1 breaker attacks."""
from __future__ import annotations

import sys
import pathlib
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from attacklib import (  # noqa: E402
    Client, PASSWORD, do_reset, fixture, seeded_total,
)

HANDLES = ("ada", "bob", "cy", "op")


@pytest.fixture
def api():
    created: list[Client] = []

    def _make(token=None, timeout=None):
        kwargs = {"token": token}
        if timeout is not None:
            kwargs["timeout"] = timeout
        c = Client(**kwargs)
        created.append(c)
        return c

    yield _make
    for c in created:
        c.close()


@pytest.fixture
def reset(api):
    def _reset(body, expect=204):
        resp = do_reset(body, expect=expect)
        if expect is not None:
            assert resp.status_code == expect, resp.text
        return resp

    return _reset


@pytest.fixture
def world(api):
    body = fixture()
    resp = do_reset(body)
    assert resp.status_code == 204, resp.text
    clients = {}
    for handle in HANDLES:
        c = api()
        login = c.login(f"{handle}@example.com", PASSWORD)
        assert login.status_code == 200, login.text
        clients[handle] = c
    return SimpleNamespace(
        fixture=body,
        total=seeded_total(body),
        currency=body["currency"],
        minor_units=body["minor_units"],
        ada=clients["ada"],
        bob=clients["bob"],
        cy=clients["cy"],
        op=clients["op"],
        all=[clients[h] for h in HANDLES],
        api=api,
    )


@pytest.fixture
def boot(reset, api):
    def _boot(body, handles=HANDLES):
        resp = reset(body)
        assert resp.status_code == 204, resp.text
        clients = {}
        for handle in handles:
            c = api()
            login = c.login(f"{handle}@example.com", PASSWORD)
            assert login.status_code == 200, login.text
            clients[handle] = c
        ns = SimpleNamespace(
            fixture=body,
            total=seeded_total(body),
            currency=body["currency"],
            minor_units=body["minor_units"],
            all=[clients[h] for h in handles],
            api=api,
        )
        for handle in handles:
            setattr(ns, handle, clients[handle])
        return ns

    return _boot


@pytest.fixture
def balance():
    def _balance(client: Client) -> int:
        return client.balance()

    return _balance


@pytest.fixture
def conservation(balance, world):
    def _check(total=None, clients=None):
        total = world.total if total is None else total
        clients = clients if clients is not None else world.all
        got = sum(balance(c) for c in clients)
        assert got == total, f"money created or destroyed: {got} != {total}"
        return got

    return _check
