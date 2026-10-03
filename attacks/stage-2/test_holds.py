"""Stage 2 — holds, /me wallet fields, authorization validation and expiry.

S2-R17 (total invariant, holds move nothing), S2-R18 (available), S2-R20 (/me fields),
S2-R21 (POST /authorizations), S2-R26 (fixture TTL), S2-R27 (expiry).
"""
from __future__ import annotations

import time

from attacklib2 import (
    assert_error,
    assert_status,
    authz,
    describe,
    fixture2,
    future_iso,
    new_key,
    past_iso,
    s1_user,
)


def wallet(client) -> dict:
    body = client.me_full()
    for field in ("balance", "total", "available", "held"):
        assert field in body, f"GET /me must expose {field!r}. got {sorted(body)}"
    assert body["balance"] == body["total"], "balance must equal total"
    return body


def test_me_no_holds_balance_total_available_agree(world):
    body = wallet(world.ada)
    assert body["held"] == 0
    assert body["available"] == body["total"] == 100_000


def test_hold_moves_no_money_only_available(world, conservation):
    before = world.total
    resp = world.ada.authorize("bob", 2_000)
    assert_status(resp, 201)
    a = resp.json()
    assert a["from_handle"] == "ada" and a["to_handle"] == "bob"
    assert a["amount"] == 2_000
    assert a["captured_amount"] == 0
    assert a["status"] == "open"
    assert a["remaining_amount"] == 2_000
    assert a["payment_id"] is None

    ada = wallet(world.ada)
    assert (ada["balance"], ada["total"], ada["held"], ada["available"]) == \
        (100_000, 100_000, 2_000, 98_000)
    bob = wallet(world.bob)
    assert bob["held"] == 0 and bob["available"] == bob["balance"] == 500
    # a hold is not a transfer: every wallet total is unchanged
    conservation()
    assert conservation() == before


def test_authorization_defaults_visibility_public_and_note_empty(world):
    resp = world.ada.authorize("bob", 700)
    assert_status(resp, 201)
    a = resp.json()
    assert a["visibility"] == "public", "visibility default must match POST /payments"
    assert a["note"] == ""


def test_authorization_idempotent_same_key_and_body(world):
    key = new_key()
    first = world.ada.authorize("bob", 2_000, key=key)
    second = world.ada.authorize("bob", 2_000, key=key)
    assert_status(first, 201)
    assert_status(second, 200)
    assert first.json() == second.json(), "a replay must return the original body"
    ada = wallet(world.ada)
    assert ada["held"] == 2_000, "a replay must not create a second hold"


def test_authorization_key_reuse_different_body_conflicts(world):
    key = new_key()
    assert_status(world.ada.authorize("bob", 2_000, key=key), 201)
    assert_error(world.ada.authorize("bob", 2_500, key=key), 409, "idempotency_key_reuse")


def test_authorization_missing_key_is_400(world):
    assert_error(world.ada.authorize("bob", 2_000, key_sent=False),
                 400, "missing_idempotency_key")


def test_authorization_never_appears_in_activity_feed(world):
    assert_status(world.ada.authorize("bob", 2_000, note="hold only"), 201)
    for reader in (world.ada, world.bob, world.cy):
        resp = assert_status(reader.get("/activity"), 200)
        body = resp.json()
        items = body.get("payments", body) if isinstance(body, dict) else body
        assert isinstance(items, list), describe(resp)
        assert items == [], f"a hold must not appear in the feed: {items}"


def test_insufficient_funds_checked_against_available_not_total(world):
    # ada holds nearly everything, leaving 1_000 available of a 100_000 total.
    assert_status(world.ada.authorize("bob", 99_000), 201)
    assert wallet(world.ada)["available"] == 1_000
    # A payment within total but above available must be refused on available.
    assert_error(world.ada.post("/payments", json={"to_handle": "bob", "amount": 50_000},
                                headers={"Idempotency-Key": new_key()}),
                 409, "insufficient_funds")
    # And another authorization above available is refused too.
    assert_error(world.ada.authorize("cy", 50_000), 409, "insufficient_funds")
    # Exactly available still succeeds.
    assert_status(world.ada.authorize("cy", 1_000), 201)
    assert wallet(world.ada)["available"] == 0


def test_authorization_validation_table(world):
    bad_amounts = [0, -1, 1_000_000_001, 1.5, "100"]
    for amount in bad_amounts:
        resp = world.ada.post("/authorizations",
                              json={"to_handle": "bob", "amount": amount},
                              headers={"Idempotency-Key": new_key()})
        assert_error(resp, 422, "validation_failed")
    assert_error(world.ada.authorize("bob", 10, note="x" * 201), 422, "validation_failed")
    assert_error(world.ada.authorize("bob", 10, visibility="secret"), 422, "validation_failed")
    assert_error(world.ada.authorize("nobody", 10), 404, "not_found")


def test_authorization_self_payment_rejected(world):
    assert_error(world.ada.authorize("ada", 10), 422, "self_payment")


def test_seeded_open_hold_derives_available(world, reset, boot):
    body = fixture2(authorizations=[authz("a_seed", "u_ada", "u_bob", 2_000,
                                          expires_at=future_iso(7200))])
    ns = boot(body)
    ada = wallet(ns.ada)
    assert (ada["balance"], ada["total"], ada["held"], ada["available"]) == \
        (100_000, 100_000, 2_000, 98_000)
    # the derived hold matches an API-created one, and reads reflect it without a write
    assert wallet(ns.bob)["held"] == 0


def test_seeded_hold_over_balance_is_reset_error_and_changes_nothing(reset, boot):
    good = fixture2()
    ns = boot(good)
    assert wallet(ns.ada)["available"] == 100_000
    bad = fixture2(authorizations=[authz("a_bad", "u_ada", "u_bob", 100_001,
                                         expires_at=future_iso(7200))])
    resp = reset(bad, expect=None)
    assert_error(resp, 422, "validation_failed")
    # the failed reset changed nothing
    assert wallet(ns.ada)["balance"] == 100_000
    assert wallet(ns.ada)["held"] == 0


def test_seeded_void_and_captured_holds_hold_nothing(world, boot):
    body = fixture2(authorizations=[
        authz("a_void", "u_ada", "u_bob", 3_000, status="voided", expires_at=future_iso()),
        authz("a_cap", "u_ada", "u_bob", 4_000, status="captured", captured_amount=4_000,
              expires_at=future_iso()),
        authz("a_open", "u_ada", "u_bob", 1_000, status="open", expires_at=future_iso()),
    ])
    ns = boot(body)
    ada = wallet(ns.ada)
    assert ada["held"] == 1_000, "only open holds reserve money"
    assert ada["available"] == 99_000


def test_ttl_default_is_600_seconds(world):
    resp = world.ada.authorize("bob", 500)
    assert_status(resp, 201)
    a = resp.json()
    created = a["created_at"]
    expires = a["expires_at"]
    import datetime as dt
    c = dt.datetime.fromisoformat(created)
    e = dt.datetime.fromisoformat(expires)
    assert (e - c).total_seconds() == 600, f"default ttl must be 600s: {created} -> {expires}"


def test_ttl_custom_and_invalid(reset, boot):
    # a positive integer is accepted and applied
    ns = boot(fixture2(ttl=1))
    a = assert_status(ns.ada.authorize("bob", 500), 201).json()
    import datetime as dt
    c = dt.datetime.fromisoformat(a["created_at"])
    e = dt.datetime.fromisoformat(a["expires_at"])
    assert (e - c).total_seconds() == 1
    # a non-positive integer is a validation error
    for ttl in (0, -5):
        assert_error(reset(fixture2(ttl=ttl), expect=None), 422, "validation_failed")
    # a non-integer or non-numeric value must be refused outright, never accepted
    for ttl in (1.5, "600"):
        resp = reset(fixture2(ttl=ttl), expect=None)
        assert resp.status_code >= 400, f"invalid ttl {ttl!r} was accepted: {resp.status_code}"


def test_expired_seeded_authorization_holds_nothing_and_reports_expired(world, boot):
    body = fixture2(authorizations=[
        authz("a_old", "u_ada", "u_bob", 5_000, status="open", expires_at=past_iso(3600)),
    ])
    ns = boot(body)
    ada = wallet(ns.ada)
    assert ada["held"] == 0, "an authorization at or before now holds no funds"
    assert ada["available"] == ada["total"] == 100_000
    listed = assert_status(ns.ada.list_authorizations(status="expired"), 200).json()
    items = listed.get("authorizations", listed)
    assert [i.get("authorization_id", i.get("id")) for i in items] == ["a_old"]


def test_expiry_releases_without_any_wall_clock_request(world, boot):
    ns = boot(fixture2(ttl=1))
    a = assert_status(ns.ada.authorize("bob", 4_000), 201).json()
    aid = a["authorization_id"]
    assert wallet(ns.ada)["held"] == 4_000
    time.sleep(1.6)
    # no request touched the service at the deadline; the next read must reflect expiry
    assert wallet(ns.ada)["held"] == 0
    assert wallet(ns.ada)["available"] == 100_000
    item = ns.ada.find_authorization(aid)
    assert item is not None and item["status"] == "expired"
    open_items = assert_status(ns.ada.list_authorizations(status="open"), 200).json()
    ids = [i.get("authorization_id", i.get("id")) for i in open_items.get("authorizations", open_items)]
    assert aid not in ids, "an expired authorization must never match status=open"


def test_fixture_may_omit_authorizations(reset, boot):
    body = fixture2(include_authorizations=False)
    assert "authorizations" not in body
    ns = boot(body)
    assert wallet(ns.ada)["held"] == 0


def test_payment_leaves_no_intermediate_hold(world):
    assert_status(world.ada.post("/payments", json={"to_handle": "bob", "amount": 1_500},
                                 headers={"Idempotency-Key": new_key()}), 201)
    body = wallet(world.ada)
    assert body["held"] == 0, "POST /payments must not leave a hold behind"
    assert body["balance"] == body["total"] == body["available"] == 98_500
    assert_status(world.ada.list_authorizations(), 200)


def test_insufficient_funds_on_request_pay_uses_available(world):
    assert_status(world.ada.authorize("bob", 99_000), 201)
    made = world.bob.post("/requests", json={"payer_handle": "ada", "amount": 50_000},
                          headers={"Idempotency-Key": new_key()})
    assert_status(made, 201)
    rid = made.json()["request_id"]
    # ada's total is still 100_000, but only 1_000 is available
    assert_error(world.ada.post(f"/requests/{rid}/pay", json={},
                                headers={"Idempotency-Key": new_key()}),
                 409, "insufficient_funds")


def test_insufficient_funds_on_settlement_uses_available(world):
    assert_status(world.ada.authorize("bob", 99_000), 201)
    body = {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 50_000}]}
    assert_error(world.op.post("/settlements", json=body,
                               headers={"Idempotency-Key": new_key()}),
                 409, "insufficient_funds")
