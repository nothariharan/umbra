"""Pytest fixtures for the stage-4 breaker attacks."""
from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from attacklib4 import (  # noqa: E402
    PASSWORD,
    S4Client,
    do_reset,
    fixture3,
    seeded_total,
)

HANDLES = ("ada", "bob", "cy", "op")


@pytest.fixture
def api():
    created: list[S4Client] = []

    def _make(token=None, timeout=None):
        kwargs = {"token": token}
        if timeout is not None:
            kwargs["timeout"] = timeout
        c = S4Client(**kwargs)
        created.append(c)
        return c

    yield _make
    for c in created:
        c.close()


@pytest.fixture
def reset():
    def _reset(body, expect=204):
        resp = do_reset(body)
        if expect is not None:
            assert resp.status_code == expect, resp.text
        return resp

    return _reset


@pytest.fixture
def boot4(api, reset):
    def _boot(body, handles=None):
        if handles is None:
            handles = tuple(u["handle"] for u in body["users"])
        reset(body)
        clients = {}
        for handle in handles:
            c = api()
            assert c.login(f"{handle}@example.com", PASSWORD).status_code == 200
            clients[handle] = c
        ns = SimpleNamespace(
            fixture=body,
            total=seeded_total(body),
            currency=body["currency"],
            minor_units=body["minor_units"],
            all=[clients[h] for h in handles],
        )
        for handle in handles:
            setattr(ns, handle, clients[handle])
        return ns

    return _boot


@pytest.fixture
def world4(api, reset):
    body = fixture3()
    reset(body)
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
        **clients,
        all=[clients[h] for h in HANDLES],
    )
    return ns
