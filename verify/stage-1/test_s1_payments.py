"""S1-C11 S1-C12: /me and POST /payments."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c11_me_shape(world):
    body = assert_status(world.ada.get("/me"), 200).json()
    assert set(body) >= {"user_id", "display_name", "handle", "balance", "currency", "minor_units"}
    assert body["handle"] == "ada"
    assert body["balance"] == fx.ADA["balance"]
    assert body["currency"] == world.currency
    assert body["minor_units"] == world.minor_units


def test_s1_c12_payment_defaults_and_move(world, pay, balance, conservation):
    before_a, before_b = balance(world.ada), balance(world.bob)
    body = assert_status(pay(amount=1500, note="dinner", visibility="public"), 201).json()
    assert body["note"] == "dinner" and body["visibility"] == "public"
    assert body["request_id"] is None
    assert balance(world.ada) == before_a - 1500
    assert balance(world.bob) == before_b + 1500
    conservation(world)


def test_s1_c12_payment_optional_defaults(world, pay):
    body = assert_status(pay(amount=100), 201).json()
    assert body["note"] == "" and body["visibility"] == "public"


def test_s1_c12_note_verbatim(world, pay):
    note = "  spaced  \temoji🎉"
    assert assert_status(pay(amount=1, note=note), 201).json()["note"] == note


@pytest.mark.parametrize("amount", [1000, 1000.0, 1e3])
def test_s1_c12_integral_amount_forms(world, pay, amount):
    assert_status(pay(amount=amount), 201)


@pytest.mark.parametrize("amount", ["100", True, 1.5])
def test_s1_c12_invalid_amount_types(world, pay, amount):
    assert_error(pay(amount=amount), 422, "validation_failed")


def test_s1_c12_payment_error_cases(world, pay, balance):
    assert_error(pay(to_handle="ada"), 422, "self_payment")
    assert_error(pay(to_handle="missing_handle_xyz"), 404, "not_found")
    assert_error(pay(world.cy, to_handle="bob", amount=balance(world.cy) + 1), 409, "insufficient_funds")
