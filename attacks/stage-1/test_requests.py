"""Request lifecycle attacks: parties, states, filters and listing.

Class: repetition and ordering / boundaries. A request has exactly one terminal
state and only its two parties may act on it.
"""
from __future__ import annotations

from attacklib import (
    Client, assert_error, assert_status, fixture, new_key, user,
)

REQ = "/requests"


def _ask(client, amount=100, *, payer_handle="ada", key=None, **extra):
    body = {"payer_handle": payer_handle, "amount": amount}
    body.update(extra)
    return client.post(REQ, json=body, headers={"Idempotency-Key": key or new_key()})


def _paid(world, amount=100):
    made = _ask(world.bob, amount, payer_handle="ada")
    assert_status(made, 201)
    rid = made.json()["request_id"]
    paid = world.ada.post(f"/requests/{rid}/pay", json={},
                          headers={"Idempotency-Key": new_key()})
    assert_status(paid, 201)
    return rid


def test_pay_by_wrong_party_is_403(world):
    made = _ask(world.bob, payer_handle="ada")
    rid = made.json()["request_id"]
    r = world.cy.post(f"/requests/{rid}/pay", json={},
                      headers={"Idempotency-Key": new_key()})
    assert_error(r, 403, "forbidden")


def test_decline_and_cancel_by_wrong_party_are_403(world):
    made = _ask(world.bob, payer_handle="ada")
    rid = made.json()["request_id"]
    assert_error(world.bob.post(f"/requests/{rid}/decline"), 403, "forbidden")
    assert_error(world.cy.post(f"/requests/{rid}/decline"), 403, "forbidden")
    assert_error(world.ada.post(f"/requests/{rid}/cancel"), 403, "forbidden")
    assert_error(world.cy.post(f"/requests/{rid}/cancel"), 403, "forbidden")


def test_unknown_request_is_404(world):
    assert_error(world.ada.post("/requests/nope/pay", json={},
                                headers={"Idempotency-Key": new_key()}),
                 404, "not_found")
    assert_error(world.ada.post("/requests/nope/decline"), 404, "not_found")
    assert_error(world.bob.post("/requests/nope/cancel"), 404, "not_found")


def test_decline_after_paid_is_409(world):
    rid = _paid(world)
    assert_error(world.ada.post(f"/requests/{rid}/decline"),
                 409, "request_not_pending")
    assert_error(world.bob.post(f"/requests/{rid}/cancel"),
                 409, "request_not_pending")


def test_cancel_after_decline_is_409_and_decline_after_cancel_is_409(world):
    made = _ask(world.bob, payer_handle="ada")
    rid = made.json()["request_id"]
    assert_status(world.ada.post(f"/requests/{rid}/decline"), 200)
    assert_error(world.bob.post(f"/requests/{rid}/cancel"),
                 409, "request_not_pending")

    made2 = _ask(world.bob, payer_handle="ada")
    rid2 = made2.json()["request_id"]
    assert_status(world.bob.post(f"/requests/{rid2}/cancel"), 200)
    assert_error(world.ada.post(f"/requests/{rid2}/decline"),
                 409, "request_not_pending")


def test_request_pay_replay_body_must_be_identical(world):
    made = _ask(world.bob, payer_handle="ada")
    rid = made.json()["request_id"]
    key = new_key()
    assert_status(world.ada.post(f"/requests/{rid}/pay", json={},
                                 headers={"Idempotency-Key": key}), 201)
    r = world.ada.post(f"/requests/{rid}/pay", json={"visibility": "public"},
                       headers={"Idempotency-Key": key})
    assert_error(r, 409, "idempotency_key_reuse")


def test_direction_filter(world):
    outgoing = _ask(world.bob, payer_handle="ada").json()["request_id"]
    incoming = _ask(world.ada, payer_handle="bob").json()["request_id"]

    bob_ids = {q["request_id"] for q in
               world.bob.get(REQ, params={"direction": "outgoing"}).json()["requests"]}
    assert outgoing in bob_ids and incoming not in bob_ids

    bob_in = {q["request_id"] for q in
              world.bob.get(REQ, params={"direction": "incoming"}).json()["requests"]}
    assert incoming in bob_in and outgoing not in bob_in

    both = {q["request_id"] for q in world.bob.get(REQ).json()["requests"]}
    assert {outgoing, incoming} <= both


def test_status_filter_and_unknown_values(world):
    pending = _ask(world.bob, payer_handle="ada").json()["request_id"]
    paid = _paid(world)
    pending_ids = {q["request_id"] for q in
                   world.ada.get(REQ, params={"status": "pending"}).json()["requests"]}
    assert pending in pending_ids and paid not in pending_ids
    for bad in ({"status": "nonsense"}, {"direction": "sideways"}):
        assert_error(world.ada.get(REQ, params=bad), 422, "validation_failed")


def test_requests_newest_first_and_has_more(world):
    ids = [_ask(world.bob, amount=10 + i, payer_handle="ada").json()["request_id"]
           for i in range(3)]
    listed = world.bob.get(REQ, params={"limit": 200}).json()["requests"]
    order = [q["request_id"] for q in listed]
    assert order == list(reversed(ids)), order
    page = world.bob.get(REQ, params={"limit": 2}).json()
    assert page["has_more"] is True
    assert len(page["requests"]) == 2


def test_other_users_requests_are_not_visible(world):
    made = _ask(world.bob, payer_handle="ada")
    rid = made.json()["request_id"]
    assert all(q["request_id"] != rid
               for q in world.cy.get(REQ).json()["requests"])


def test_write_endpoints_require_auth(boot):
    w = boot(fixture(), handles=("ada",))
    anon = Client()
    try:
        assert_error(anon.post("/payments", json={"to_handle": "ada", "amount": 1},
                               headers={"Idempotency-Key": new_key()}),
                     401, "unauthenticated")
        assert_error(anon.get(REQ), 401, "unauthenticated")
        assert_error(anon.get("/activity"), 401, "unauthenticated")
    finally:
        anon.close()
