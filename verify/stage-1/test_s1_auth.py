"""S1-C9 S1-C10: auth, signup handle derivation, password storage."""
from __future__ import annotations

import json

import pytest

from lib import fixtures as fx
from lib.http import assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(1)


def test_s1_c9_signup_login_and_me(world, api, balance):
    email = "new.user@example.com"
    resp = assert_status(world.ada.signup(email, "correct horse", "New User"), 201)
    body = resp.json()
    assert body["user_id"] and body["display_name"] == "New User" and body["token"]
    client = api(body["token"])
    me = assert_status(client.get("/me"), 200).json()
    assert me["handle"] == fx.derive_handle(email)
    assert balance(client) == 0
    again = world.ada.signup(email, "correct horse", "Dup")
    assert_error(again, 409, "email_taken")


def test_s1_c9_signup_short_password_and_bad_email(world):
    assert_error(world.ada.signup("bad", "short", "X"), 422, "validation_failed")
    assert_error(world.ada.signup("not-an-email", "correct horse", "X"), 422, "validation_failed")


def test_s1_c9_handle_taken_on_signup(world, api):
    # New email whose derived handle collides with seeded ada, without email_taken.
    assert_error(world.ada.signup("Ada@other.example.com", "correct horse", "Ada2"), 409, "handle_taken")


def test_s1_c9_login_success_and_unauthenticated(world, api):
    ok = world.ada.login(fx.ADA["email"], fx.ADA["password"])
    assert_status(ok, 200)
    assert_error(world.ada.login(fx.ADA["email"], "wrong password"), 401, "unauthenticated")
    assert_error(world.ada.login("missing@example.com", fx.ADA["password"]), 401, "unauthenticated")


def test_s1_c9_bearer_required_except_public_paths(world, api, reset):
    assert_error(world.ada.get("/me", token=None), 401, "unauthenticated")
    assert_status(api().get("/health", token=None), 200)
    assert reset(fx.fixture(), raw=True).status_code == 204
    snap = api().get("/_test/export", token=None)
    assert snap.status_code == 200


def test_s1_c10_export_state_does_not_store_plaintext_password(reset, api):
    secret = "unique-secret-horse-99"
    fx_body = fx.fixture(users=[fx.user("zee", 0, email="zee@example.com", password=secret)])
    reset(fx_body)
    blob = json.dumps(api().get("/_test/export", token=None).json())
    assert secret not in blob
