"""S1-C23: export/import round trip."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c23_export_shape(world):
    snap = assert_status(world.ada.get("/_test/export", token=None), 200).json()
    assert snap["track"] == "pocketful"
    assert snap["format_version"] == 1
    assert "state" in snap


def test_s1_c23_import_round_trip_preserves_payment(world, pay, reset):
    receipt = assert_status(pay(amount=77, note="keep"), 201).json()
    token = world.ada.token
    snap = world.ada.get("/_test/export", token=None).json()
    reset(world.fixture)
    ada = world.ada.__class__(world.ada.base_url)
    ada.authenticate(fx.ADA["email"], fx.ADA["password"])
    assert ada.get("/activity").json()["payments"] == []
    assert_status(ada.post("/_test/import", json=snap, token=None), 204)
    ada.token = token
    feed = ada.get("/activity").json()["payments"]
    assert feed and feed[0]["payment_id"] == receipt["payment_id"]
    assert feed[0]["note"] == "keep"


def test_s1_c23_invalid_import_unchanged(world, pay):
    before = world.ada.get("/me").json()["balance"]
    assert_error(world.ada.post("/_test/import", json={"track": "wrong"}, token=None), 422, "validation_failed")
    assert world.ada.get("/me").json()["balance"] == before
