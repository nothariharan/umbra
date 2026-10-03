"""Stage 2 — capture, void, capture errors and authorization listing.

S2-R17 (total invariant), S2-R18 (available), S2-R19 (capture invariant),
S2-R22 (POST capture), S2-R23 (capture errors), S2-R24 (void), S2-R25 (GET list).
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
)


def wallet(client) -> dict:
    body = client.me_full()
    for field in ("balance", "total", "available", "held"):
        assert field in body, f"GET /me must expose {field!r}. got {sorted(body)}"
    return body


def open_authz(ns, frm="ada", to="bob", amount=2_000, **kw):
    resp = getattr(ns, frm).authorize(to, amount, **kw)
    assert_status(resp, 201)
    return resp.json()["authorization_id"]


def payment_items(client) -> list:
    resp = assert_status(client.get("/activity"), 200)
    body = resp.json()
    items = body.get("payments", body) if isinstance(body, dict) else body
    assert isinstance(items, list), describe(resp)
    return items


def test_full_final_capture_moves_money_and_closes(world, conservation):
    aid = open_authz(world, amount=2_000)
    resp = world.bob.capture(aid, 2_000)
    assert_status(resp, 201)
    p = resp.json()
    assert p["authorization_id"] == aid
    assert p["request_id"] is None
    assert p["from_handle"] == "ada" and p["to_handle"] == "bob"
    assert p["amount"] == 2_000

    assert wallet(world.ada)["held"] == 0
    assert (wallet(world.ada)["total"], wallet(world.bob)["total"]) == (98_000, 2_500)
    item = world.ada.find_authorization(aid)
    assert item is not None and item["status"] == "captured"
    assert item["remaining_amount"] == 0
    conservation()


def test_partial_final_capture_releases_remainder_immediately(world, conservation):
    aid = open_authz(world, amount=2_000)
    assert_status(world.bob.capture(aid, 1_500), 201)
    ada = wallet(world.ada)
    assert ada["held"] == 0, "a final capture releases the uncaptured remainder"
    assert ada["total"] == 98_500 and ada["available"] == 98_500
    assert wallet(world.bob)["total"] == 2_000
    conservation()


def test_second_capture_after_final_capture_is_not_open(world):
    aid = open_authz(world, amount=2_000)
    assert_status(world.bob.capture(aid, 1_000), 201)
    assert_error(world.bob.capture(aid, 500), 409, "authorization_not_open")


def test_extended_capture_keeps_remainder_held(world):
    aid = open_authz(world, amount=2_000)
    resp = world.bob.capture(aid, 700, final=False)
    assert_status(resp, 201)
    item = world.ada.find_authorization(aid)
    assert item["status"] == "open", "final:false with a remainder keeps the hold open"
    assert item["captured_amount"] == 700
    assert item["remaining_amount"] == 1_300
    assert wallet(world.ada)["held"] == 1_300
    assert wallet(world.ada)["available"] == 98_000, \
        "a nonfinal capture moves money and releases the same hold, so available is unchanged"
    # further captures up to the remainder are allowed
    assert_status(world.bob.capture(aid, 1_300, final=False), 201)
    item = world.ada.find_authorization(aid)
    assert item["status"] == "captured", "capturing the whole remainder closes it"
    assert item["remaining_amount"] == 0
    assert wallet(world.ada)["held"] == 0


def test_capture_exceeding_remaining_is_422(world):
    aid = open_authz(world, amount=2_000)
    assert_status(world.bob.capture(aid, 700, final=False), 201)
    assert_error(world.bob.capture(aid, 1_301, final=False), 422,
                 "capture_exceeds_authorization")
    # the over-capture must not have moved money or changed the hold
    assert wallet(world.ada)["held"] == 1_300


def test_capture_invalid_amount_is_422(world):
    aid = open_authz(world, amount=2_000)
    for amount in (0, -1, 1.5, "100"):
        resp = world.bob.post(f"/authorizations/{aid}/capture",
                              json={"amount": amount},
                              headers={"Idempotency-Key": new_key()})
        assert_error(resp, 422, "validation_failed")


def test_omitted_amount_captures_remaining(world):
    aid = open_authz(world, amount=2_000)
    resp = world.bob.capture(aid, body={})
    assert_status(resp, 201)
    assert resp.json()["amount"] == 2_000
    assert world.ada.find_authorization(aid)["status"] == "captured"


def test_capture_body_equality_is_byte_exact(world):
    aid = open_authz(world, amount=2_000)
    key = new_key()
    assert_status(world.bob.capture(aid, body={"amount": 2_000}, key=key), 201)
    # `{}` and `{"amount": 2000}` mean the same capture but are different JSON values
    assert_error(world.bob.capture(aid, body={}, key=key), 409, "idempotency_key_reuse")


def test_capture_idempotent_replay_moves_money_once(world, conservation):
    aid = open_authz(world, amount=2_000)
    key = new_key()
    first = world.bob.capture(aid, 1_500, key=key)
    second = world.bob.capture(aid, 1_500, key=key)
    assert_status(first, 201)
    assert_status(second, 200)
    assert first.json() == second.json()
    assert wallet(world.ada)["total"] == 98_500, "a replay must move money once"
    conservation()


def test_capture_receiver_only(world):
    aid = open_authz(world, amount=2_000)
    assert_error(world.ada.capture(aid, 100), 403, "forbidden")
    assert_error(world.cy.capture(aid, 100), 403, "forbidden")


def test_capture_unknown_authorization_is_404(world):
    assert_error(world.bob.capture("a_nope", 100), 404, "not_found")


def test_capture_expired_by_clock_is_authorization_expired(world, boot):
    ns = boot(fixture2(ttl=1))
    aid = open_authz(ns, amount=2_000)
    time.sleep(1.6)
    assert_error(ns.bob.capture(aid, 100), 409, "authorization_expired")
    assert wallet(ns.ada)["held"] == 0


def test_capture_voided_is_not_open(world):
    aid = open_authz(world, amount=2_000)
    assert_status(world.ada.void(aid), 200)
    assert_error(world.bob.capture(aid, 100), 409, "authorization_not_open")


def test_void_payer_only_and_idempotent(world):
    aid = open_authz(world, amount=2_000)
    first = world.ada.void(aid)
    second = world.ada.void(aid)
    assert_status(first, 200)
    assert_status(second, 200)
    assert first.json()["status"] == "voided"
    assert second.json()["status"] == "voided"
    assert wallet(world.ada)["held"] == 0
    assert_error(world.bob.void(aid), 403, "forbidden")
    assert_error(world.cy.void(aid), 403, "forbidden")


def test_void_captured_and_expired_are_not_open(world, boot):
    aid = open_authz(world, amount=2_000)
    assert_status(world.bob.capture(aid, 2_000), 201)
    assert_error(world.ada.void(aid), 409, "authorization_not_open")

    ns = boot(fixture2(authorizations=[
        authz("a_old", "u_ada", "u_bob", 3_000, status="open", expires_at=past_iso(600))]))
    assert_error(ns.ada.void("a_old"), 409, "authorization_not_open")


def test_captured_payment_follows_feed_visibility(world):
    aid = open_authz(world, amount=2_000, visibility="private", note="secret hold")
    assert_status(world.bob.capture(aid, 1_000), 201)
    # sender and receiver see it; a third party does not
    assert len(payment_items(world.ada)) == 1
    assert len(payment_items(world.bob)) == 1
    assert payment_items(world.cy) == []


def test_capture_records_are_cumulative(world):
    aid = open_authz(world, amount=2_000)
    p1 = assert_status(world.bob.capture(aid, 700, final=False), 201).json()
    p2 = assert_status(world.bob.capture(aid, 800, final=False), 201).json()
    item = world.ada.find_authorization(aid)
    assert item["captured_amount"] == 1_500
    assert item["remaining_amount"] == 500
    assert item["payment_id"] == p2["payment_id"], "payment_id is the latest capture"
    assert item["payment_ids"] == [p1["payment_id"], p2["payment_id"]]


def test_void_after_partial_capture_releases_only_remainder(world, conservation):
    aid = open_authz(world, amount=2_000)
    p1 = assert_status(world.bob.capture(aid, 700, final=False), 201).json()
    assert_status(world.ada.void(aid), 200)
    item = world.ada.find_authorization(aid)
    assert item["status"] == "voided"
    assert item["captured_amount"] == 700, "capture records survive a void"
    assert p1["payment_id"] in item["payment_ids"]
    assert wallet(world.ada)["held"] == 0
    assert wallet(world.ada)["total"] == 99_300
    conservation()


def test_authorization_listing_scope_and_filters(world):
    a_out = open_authz(world, frm="ada", to="bob", amount=1_000)
    a_in = open_authz(world, frm="cy", to="ada", amount=2_000)
    a_void = open_authz(world, frm="ada", to="cy", amount=3_000)
    assert_status(world.ada.void(a_void), 200)

    outgoing = assert_status(world.ada.list_authorizations(direction="outgoing"), 200).json()
    ids = {i["authorization_id"] for i in outgoing["authorizations"]}
    assert ids == {a_out, a_void}, "caller only sees authorizations they are party to"
    incoming = assert_status(world.ada.list_authorizations(direction="incoming"), 200).json()
    assert {i["authorization_id"] for i in incoming["authorizations"]} == {a_in}
    open_out = assert_status(world.ada.list_authorizations(direction="outgoing", status="open"),
                             200).json()
    assert {i["authorization_id"] for i in open_out["authorizations"]} == {a_out}
    all_ada = assert_status(world.ada.list_authorizations(), 200).json()
    assert {i["authorization_id"] for i in all_ada["authorizations"]} == {a_out, a_in, a_void}

    stranger = assert_status(world.op.list_authorizations(), 200).json()
    assert stranger["authorizations"] == []


def test_authorization_listing_pagination(world):
    for i in range(3):
        open_authz(world, frm="ada", to="bob", amount=100 + i)
    page = assert_status(world.ada.list_authorizations(limit=1, offset=0), 200).json()
    assert len(page["authorizations"]) == 1
    assert page["has_more"] is True
    rest = assert_status(world.ada.list_authorizations(limit=10, offset=1), 200).json()
    assert len(rest["authorizations"]) == 2
    assert rest["has_more"] is False
