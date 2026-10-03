"""Durability attacks: export and import round trips.

Class: durability. State moved through export/import must come back unchanged:
balances, tokens, idempotency records and timestamps.
"""
from __future__ import annotations

from attacklib import (
    Client, assert_error, assert_status, do_reset, fixture, new_key, user,
)

EXPORT = "/_test/export"
IMPORT = "/_test/import"
PAY = "/payments"


def _export():
    c = Client()
    try:
        return c.get(EXPORT, token=None)
    finally:
        c.close()


def _import(obj):
    c = Client()
    try:
        return c.post(IMPORT, json=obj, token=None)
    finally:
        c.close()


def _import_raw(raw: bytes):
    c = Client()
    try:
        return c.post(IMPORT, content=raw, headers={"Content-Type": "application/json"},
                      token=None)
    finally:
        c.close()


def test_export_shape(world):
    r = _export()
    assert_status(r, 200)
    body = r.json()
    assert body["track"] == "pocketful"
    assert body["format_version"] == 1
    assert "state" in body


def test_round_trip_preserves_balances_tokens_and_receipts(world):
    key = new_key()
    first = world.ada.post(PAY, json={"to_handle": "bob", "amount": 123},
                           headers={"Idempotency-Key": key})
    assert_status(first, 201)
    pid = first.json()["payment_id"]
    created = first.json()["created_at"]
    ada_after = world.ada.balance()
    bob_after = world.bob.balance()

    snapshot = _export()
    assert_status(snapshot, 200)

    world.ada.post(PAY, json={"to_handle": "cy", "amount": 50},
                   headers={"Idempotency-Key": new_key()})
    assert world.ada.balance() != ada_after

    assert_status(_import(snapshot.json()), 204)

    assert world.ada.balance() == ada_after
    assert world.bob.balance() == bob_after
    assert world.ada.get("/me").status_code == 200, "token did not survive import"

    replay = world.ada.post(PAY, json={"to_handle": "bob", "amount": 123},
                            headers={"Idempotency-Key": key})
    assert_status(replay, 200)
    assert replay.json() == first.json(), "idempotency record did not survive import"

    feed = world.ada.get("/activity").json()["payments"]
    saved = next(p for p in feed if p["payment_id"] == pid)
    assert saved["created_at"] == created, "timestamp was regenerated on import"


def test_repeated_import_does_not_duplicate(world):
    snapshot = _export().json()
    assert_status(_import(snapshot), 204)
    ada = world.ada.balance()
    bob = world.bob.balance()
    assert_status(_import(snapshot), 204)
    assert world.ada.balance() == ada
    assert world.bob.balance() == bob


def test_export_is_a_read_only_snapshot(world):
    assert_status(world.ada.post(PAY, json={"to_handle": "bob", "amount": 100},
                                 headers={"Idempotency-Key": new_key()}), 201)
    snapshot = _export().json()
    assert_status(world.ada.post(PAY, json={"to_handle": "bob", "amount": 100},
                                 headers={"Idempotency-Key": new_key()}), 201)
    assert_status(_import(snapshot), 204)
    assert world.ada.balance() == 99_900, "the old snapshot did not restore state"


def test_invalid_import_is_422_and_unchanged(world):
    before = world.ada.balance()
    good = _export().json()
    for bad in (
        {"format_version": 1, "state": good["state"]},
        {"track": "not-pocketful", "format_version": 1, "state": good["state"]},
        {"track": "pocketful", "format_version": 2, "state": good["state"]},
        {"track": "pocketful", "format_version": 1},
    ):
        assert_error(_import(bad), 422, "validation_failed")
    assert_error(_import_raw(b"{not json"), 422, "validation_failed")
    assert world.ada.balance() == before, "a rejected import changed state"


def test_reset_clears_imported_state(world):
    snapshot = _export().json()
    assert_status(_import(snapshot), 204)
    assert_status(do_reset(fixture()), 204)
    other = fixture(users=[user("ada", 7), user("bob", 0)], operators=[])
    assert_status(do_reset(other), 204)
    login = world.ada.login("ada@example.com")
    assert_status(login, 200)
    assert world.ada.balance() == 7, "reset did not clear imported state"
