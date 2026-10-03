"""Boundary attacks: splits, pagination, signup handles, query forms.

Class: boundaries. Inputs at, just inside and just outside every stated limit.
"""
from __future__ import annotations

from attacklib import (
    Client, assert_error, assert_status, do_reset, fixture, new_key, user,
)

SPLIT = "/splits"


def _split(client, *, amount, participants, note=None, key=None):
    body = {"amount": amount, "participant_handles": participants}
    if note is not None:
        body["note"] = note
    return client.post(SPLIT, json=body, headers={"Idempotency-Key": key or new_key()})


def _shares(resp):
    return [s["amount"] for s in resp.json()["shares"]]


def test_split_rounding_table(world):
    cases = [
        (1000, ["ada", "bob", "cy"], [334, 333, 333]),
        (1, ["ada", "bob", "cy"], [1, 0, 0]),
        (10, ["ada", "bob", "cy"], [4, 3, 3]),
        (999, ["ada", "bob", "cy"], [333, 333, 333]),
    ]
    for amount, participants, expected in cases:
        r = _split(world.ada, amount=amount, participants=participants)
        assert_status(r, 201)
        assert _shares(r) == expected, (amount, _shares(r))


def test_split_rounding_five_ways(boot):
    w = boot(fixture(users=[user("ada", 100), user("bob", 0), user("cy", 0),
                            user("dave", 0), user("eve", 0)]),
             handles=("ada", "bob", "cy", "dave", "eve"))
    r = _split(w.ada, amount=5, participants=["ada", "bob", "cy", "dave", "eve"])
    assert_status(r, 201)
    assert _shares(r) == [1, 1, 1, 1, 1]


def test_split_extra_unit_follows_the_order(world):
    first = _split(world.ada, amount=10, participants=["ada", "bob", "cy"])
    second = _split(world.ada, amount=10, participants=["bob", "ada", "cy"])
    assert _shares(first) == [4, 3, 3]
    assert _shares(second) == [4, 3, 3]
    assert first.json()["shares"][0]["handle"] == "ada"
    assert second.json()["shares"][0]["handle"] == "bob"


def test_split_zero_share_still_creates_a_request(world):
    r = _split(world.ada, amount=1, participants=["ada", "bob"])
    assert_status(r, 201)
    assert _shares(r) == [1, 0]
    assert len(r.json()["requests"]) == 1
    assert r.json()["requests"][0]["amount"] == 0


def test_split_sole_participant_caller_creates_no_requests(world):
    r = _split(world.ada, amount=42, participants=["ada"])
    assert_status(r, 201)
    assert r.json()["requests"] == []
    assert _shares(r) == [42]


def test_split_shares_sum_and_spread_property(world):
    for amount in range(1, 51):
        r = _split(world.ada, amount=amount, participants=["ada", "bob", "cy"])
        assert_status(r, 201)
        shares = _shares(r)
        assert sum(shares) == amount, (amount, shares)
        assert max(shares) - min(shares) <= 1, (amount, shares)


def test_split_invalid_inputs(world):
    r = _split(world.ada, amount=100, participants=[])
    assert_error(r, 422, "validation_failed")
    r = _split(world.ada, amount=100, participants=["bob", "bob"])
    assert_error(r, 422, "validation_failed")
    r = _split(world.ada, amount=100, participants=["bob", "ghost"])
    assert_error(r, 404, "not_found")
    r = _split(world.ada, amount=0, participants=["bob"])
    assert_error(r, 422, "validation_failed")
    r = _split(world.ada, amount=100, participants=["bob"], note="n" * 201)
    assert_error(r, 422, "validation_failed")


def test_pagination_limit_offset_bounds(world):
    for path in ("/activity", "/requests"):
        for query in ({"limit": 0}, {"limit": 201}, {"offset": -1},
                      {"limit": "4.0"}, {"limit": "1e9"}, {"offset": "+4"},
                      {"limit": "abc"}):
            r = world.ada.get(path, params=query)
            assert_error(r, 422, "validation_failed")
        for query in ({"limit": 1}, {"limit": 200}, {"offset": 0},
                      {"offset": 5}, {"bogus": "ignored"}):
            r = world.ada.get(path, params=query)
            assert_status(r, 200)


def test_pagination_has_more_and_newest_first(world):
    for i in range(3):
        r = world.ada.post("/payments", json={"to_handle": "bob", "amount": 10 + i},
                           headers={"Idempotency-Key": new_key()})
        assert_status(r, 201)
    page = world.ada.get("/activity", params={"limit": 2}).json()
    assert len(page["payments"]) == 2
    assert page["has_more"] is True
    page2 = world.ada.get("/activity", params={"limit": 2, "offset": 2}).json()
    assert page2["has_more"] is False


def _signup(email, password="correct horse", display_name="New"):
    c = Client()
    try:
        return c.post("/auth/signup",
                      json={"email": email, "password": password,
                            "display_name": display_name}, token=None)
    finally:
        c.close()


def test_signup_derives_and_truncates_handle(boot):
    w = boot(fixture(), handles=("ada",))
    r = _signup("Ada.Lovelace+1@example.com")
    assert_status(r, 201)
    token = r.json()["token"]
    c = Client(token=token)
    try:
        assert c.me()["handle"] == "ada_lovelace_1"
    finally:
        c.close()
    r = _signup("abcdefghijklmnopqrstuvwxyz@example.com")
    assert_status(r, 201)
    c = Client(token=r.json()["token"])
    try:
        assert c.me()["handle"] == "abcdefghijklmnopqrst"
    finally:
        c.close()


def test_signup_conflicts(boot):
    boot(fixture(), handles=("ada",))
    r = _signup("ada@example.com")
    assert_error(r, 409, "email_taken")
    r = _signup("ada@other.example")
    assert_error(r, 409, "handle_taken")
    r = _signup("short@example.com", password="short")
    assert_error(r, 422, "validation_failed")
    r = _signup("not-an-email")
    assert_error(r, 422, "validation_failed")


def test_login_failures(world):
    c = Client()
    try:
        assert_error(c.login("ada@example.com", "wrong password"),
                     401, "unauthenticated")
        assert_error(c.login("nobody@example.com", "correct horse"),
                     401, "unauthenticated")
    finally:
        c.close()


def test_missing_and_bad_tokens(world):
    anon = Client()
    try:
        assert_error(anon.get("/me"), 401, "unauthenticated")
        assert_error(anon.get("/me", headers={"Authorization": "Bearer nope"}),
                     401, "unauthenticated")
        assert_error(anon.get("/me", headers={"Authorization": "Basic abc"}),
                     401, "unauthenticated")
    finally:
        anon.close()


def test_reset_repeatable_and_validates_minor_units(world):
    assert_status(do_reset(fixture()), 204)
    bad = fixture(users=[user("ada", 10), user("bob", 0)], minor_units=1)
    assert_error(do_reset(bad), 422, "validation_failed")
    assert_status(do_reset(fixture()), 204)


def test_unknown_body_fields_are_ignored(world):
    r = world.ada.post("/payments",
                       json={"to_handle": "bob", "amount": 10,
                             "future_field": {"x": 1}},
                       headers={"Idempotency-Key": new_key()})
    assert_status(r, 201)
