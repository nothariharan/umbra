"""S1-C21 S1-C22: idempotency keys and shared field validation."""
from __future__ import annotations

import pytest

from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c22_missing_idempotency_key(world, pay):
    resp = world.ada.post("/payments", json={"to_handle": "bob", "amount": 1})
    assert_error(resp, 400, "missing_idempotency_key")


def test_s1_c22_idempotency_replay_and_reuse(world, pay, balance, conservation):
    key = new_key()
    first = assert_status(pay(amount=300, key=key), 201).json()
    replay = assert_status(pay(amount=300, key=key), 200).json()
    assert replay == first
    assert_error(
        world.ada.post(
            "/payments", json={"to_handle": "bob", "amount": 301}, idempotency_key=key
        ),
        409,
        "idempotency_key_reuse",
    )
    conservation(world)


def test_s1_c22_key_reusable_after_4xx(world, pay):
    key = new_key()
    assert_error(
        world.ada.post("/payments", json={"to_handle": "bob", "amount": 0}, idempotency_key=key),
        422,
        "validation_failed",
    )
    assert_status(pay(amount=10, key=key), 201)


def test_s1_c21_idempotency_key_length(world, pay):
    assert_error(pay(key=""), 400, "missing_idempotency_key")
    assert_error(pay(key="x" * 256), 422, "validation_failed")
    assert_status(pay(key="x" * 255, amount=1), 201)


def test_s1_c21_limit_offset_ranges(world):
    assert_error(world.ada.get("/activity", params={"limit": 0}), 422, "validation_failed")
    assert_error(world.ada.get("/activity", params={"limit": 201}), 422, "validation_failed")
    assert_error(world.ada.get("/activity", params={"offset": -1}), 422, "validation_failed")
