"""S1-C4 S1-C5 S1-C6 S1-C7: health, reset, conventions, id length."""
from __future__ import annotations

import json
import re

import httpx
import pytest

from lib import fixtures as fx
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c4_health_returns_ok_json(base_url):
    resp = httpx.get(f"{base_url}/health", timeout=5.0)
    assert_status(resp, 200)
    assert resp.json() == {"status": "ok"}
    ctype = resp.headers.get("content-type", "")
    assert "application/json" in ctype


def test_s1_c5_reset_replaces_state_and_supports_repeat(reset, api):
    reset(fx.fixture())
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    assert ada.get("/me").json()["balance"] == fx.ADA["balance"]
    reset(fx.fixture(users=[fx.user("ada", 100), fx.user("bob", 200)]))
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    assert ada.get("/me").json()["balance"] == 100
    resp = httpx.post(f"{ada.base_url}/_test/reset", json=fx.fixture(), timeout=10.0)
    assert resp.status_code == 204
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    assert ada.get("/me").json()["balance"] == fx.ADA["balance"]


def test_s1_c5_reset_requires_no_auth(api):
    resp = api().post("/_test/reset", json=fx.fixture(), token=None, timeout=10.0)
    assert resp.status_code == 204


def test_s1_c6_unknown_body_fields_ignored(world, pay):
    resp = pay(extra_field=123, note="x")
    assert_status(resp, 201)


def test_s1_c6_unknown_query_params_ignored(world):
    resp = world.ada.get("/activity", params={"unknown_filter": "x"})
    assert_status(resp, 200)


def test_s1_c6_created_at_has_rfc3339_offset(world, pay):
    body = assert_status(pay(amount=10), 201).json()
    ts = body["created_at"]
    assert re.search(r"[+-]\d{2}:\d{2}$", ts), ts


def test_s1_c7_resource_ids_at_most_64_chars(world, pay):
    body = assert_status(pay(amount=10), 201).json()
    for key in ("payment_id", "from_user_id", "to_user_id"):
        assert isinstance(body[key], str) and len(body[key]) <= 64


def test_s1_c8_negative_fixture_rejected(reset, api):
    reset(fx.fixture())
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    before = ada.get("/me").json()["balance"]
    broken = fx.fixture(users=[fx.user("ada", -1), fx.user("bob", 100)])
    assert_error(reset(broken, raw=True), 422, "validation_failed")
    assert ada.get("/me").json()["balance"] == before
