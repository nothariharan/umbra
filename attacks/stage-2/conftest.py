"""Pytest fixtures for the stage-2 breaker attacks."""
from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from attacklib2 import (  # noqa: E402
    PASSWORD,
    AuthClient,
    do_reset,
    fixture2,
    seeded_total,
)

HANDLES = ("ada", "bob", "cy", "op")


@pytest.fixture
def api():
    created: list[AuthClient] = []

    def _make(token=None, timeout=None):
        kwargs = {"token": token}
        if timeout is not None:
            kwargs["timeout"] = timeout
        c = AuthClient(**kwargs)
        created.append(c)
        return c

    yield _make
    for c in created:
        c.close()


@pytest.fixture
def reset():
    def _reset(body, expect=204):
        resp = do_reset(body, expect=expect)
        if expect is not None:
            assert resp.status_code == expect, resp.text
        return resp

    return _reset


@pytest.fixture
def boot(reset, api):
    def _boot(body, handles=HANDLES):
        reset(body)
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
def world(api):
    body = fixture2()
    resp = do_reset(body)
    assert resp.status_code == 204, resp.text
    clients = {}
    for handle in HANDLES:
        c = api()
        assert c.login(f"{handle}@example.com", PASSWORD).status_code == 200
        clients[handle] = c
    ns = SimpleNamespace(
        fixture=body,
        total=seeded_total(body),
        currency=body["currency"],
        minor_units=body["minor_units"],
        ada=clients["ada"],
        bob=clients["bob"],
        cy=clients["cy"],
        op=clients["op"],
        all=[clients[h] for h in HANDLES],
    )
    return ns


@pytest.fixture
def conservation(world):
    """Sum of wallet totals equals the seeded total at call time."""

    def _check():
        got = sum(c.me_full().get("total", c.me_full()["balance"]) for c in world.all)
        assert got == world.total, f"money created or destroyed: {got} != {world.total}"
        return got

    return _check
