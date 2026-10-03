"""Balance and conservation attacks.

Class: boundaries / durability of the ledger. Money is conserved, never negative,
and every 4xx leaves the ledger exactly as it was.
"""
from __future__ import annotations

from attacklib import (
    assert_error, assert_status, do_reset, fixture, new_key, user, seeded_total,
)

PAY = "/payments"
REQ = "/requests"


def _pay(client, amount, *, to_handle="bob", key=None, **extra):
    body = {"to_handle": to_handle, "amount": amount}
    body.update(extra)
    return client.post(PAY, json=body, headers={"Idempotency-Key": key or new_key()})


def _request(client, amount, *, payer_handle="ada", key=None, **extra):
    body = {"payer_handle": payer_handle, "amount": amount}
    body.update(extra)
    return client.post(REQ, json=body, headers={"Idempotency-Key": key or new_key()})


def test_exact_balance_can_be_drained_exactly_once(boot):
    w = boot(fixture(users=[user("ada", 1000), user("bob", 0)]), handles=("ada", "bob"))
    assert_status(_pay(w.ada, 1000), 201)
    assert w.ada.balance() == 0
    assert w.bob.balance() == 1000
    r = _pay(w.ada, 1)
    assert_error(r, 409, "insufficient_funds")
    assert w.ada.balance() == 0, "a failed payment moved money"
    assert w.bob.balance() == 1000


def test_failed_payment_leaves_no_trace_in_feed(world):
    before = len(world.ada.get("/activity").json()["payments"])
    r = _pay(world.ada, 10_000_000)
    assert_error(r, 409, "insufficient_funds")
    after = len(world.ada.get("/activity").json()["payments"])
    assert before == after


def test_request_may_exceed_payer_balance_and_pay_is_blocked(boot):
    w = boot(fixture(users=[user("ada", 0), user("bob", 0), user("cy", 100)]),
             handles=("ada", "bob", "cy"))
    made = _request(w.bob, 100, payer_handle="ada")
    assert_status(made, 201)
    assert made.json()["status"] == "pending"
    rid = made.json()["request_id"]

    short = w.ada.post(f"/requests/{rid}/pay", json={},
                       headers={"Idempotency-Key": new_key()})
    assert_error(short, 409, "insufficient_funds")
    assert w.ada.balance() == 0 and w.bob.balance() == 0

    assert_status(w.cy.post(PAY, json={"to_handle": "ada", "amount": 100},
                            headers={"Idempotency-Key": new_key()}), 201)
    paid = w.ada.post(f"/requests/{rid}/pay", json={},
                      headers={"Idempotency-Key": new_key()})
    assert_status(paid, 201)
    assert w.ada.balance() == 0
    assert w.bob.balance() == 100
    assert w.ada.balance() + w.bob.balance() + w.cy.balance() == w.total


def test_insufficient_request_pay_changes_nothing(world):
    made = _request(world.bob, 100_000_000, payer_handle="ada")
    assert_status(made, 201)
    rid = made.json()["request_id"]
    before = world.ada.balance()
    r = world.ada.post(f"/requests/{rid}/pay", json={},
                       headers={"Idempotency-Key": new_key()})
    assert_error(r, 409, "insufficient_funds")
    assert world.ada.balance() == before
    req = next(q for q in world.bob.get(REQ).json()["requests"]
               if q["request_id"] == rid)
    assert req["status"] == "pending", "a failed pay mutated the request"


def test_reset_with_negative_balance_is_422_and_changes_nothing(world):
    before = world.ada.balance()
    bad = fixture(users=[user("ada", -1), user("bob", 0)])
    resp = do_reset(bad)
    assert_error(resp, 422, "validation_failed")
    assert world.ada.balance() == before, "a rejected reset leaked partial state"


def test_private_payment_hidden_from_third_party(world):
    r = _pay(world.ada, 10, to_handle="bob", visibility="private")
    assert_status(r, 201)
    pid = r.json()["payment_id"]
    for who in (world.ada, world.bob):
        feed = who.get("/activity").json()["payments"]
        assert any(p["payment_id"] == pid for p in feed), "party cannot see its own payment"
    feed = world.cy.get("/activity").json()["payments"]
    assert all(p["payment_id"] != pid for p in feed), "private payment leaked to a third party"


def test_public_payment_visible_to_a_third_party(world):
    r = _pay(world.ada, 10, to_handle="bob", visibility="public")
    assert_status(r, 201)
    pid = r.json()["payment_id"]
    feed = world.cy.get("/activity").json()["payments"]
    assert any(p["payment_id"] == pid for p in feed)


def test_requests_never_appear_in_activity(world):
    made = _request(world.bob, 100, payer_handle="ada")
    assert_status(made, 201)
    assert world.bob.get("/activity").json()["payments"] == []
    assert world.ada.get("/activity").json()["payments"] == []


def test_request_pay_default_visibility_is_public(world):
    made = _request(world.bob, 100, payer_handle="ada")
    rid = made.json()["request_id"]
    paid = world.ada.post(f"/requests/{rid}/pay", json={},
                          headers={"Idempotency-Key": new_key()})
    assert_status(paid, 201)
    assert paid.json()["visibility"] == "public"
    pid = paid.json()["payment_id"]
    assert any(p["payment_id"] == pid
               for p in world.cy.get("/activity").json()["payments"])


def test_request_pay_visibility_is_the_payers_choice(world):
    made = _request(world.bob, 100, payer_handle="ada")
    rid = made.json()["request_id"]
    paid = world.ada.post(f"/requests/{rid}/pay", json={"visibility": "private"},
                          headers={"Idempotency-Key": new_key()})
    assert_status(paid, 201)
    assert paid.json()["visibility"] == "private"
    pid = paid.json()["payment_id"]
    assert all(p["payment_id"] != pid
               for p in world.cy.get("/activity").json()["payments"])
    assert any(p["payment_id"] == pid
               for p in world.bob.get("/activity").json()["payments"])


def test_note_is_returned_verbatim(world):
    raw = "  Dinner \u2014 \u00e9\u00e8 \U0001f35c\ttab  "
    r = _pay(world.ada, 10, note=raw)
    assert_status(r, 201)
    assert r.json()["note"] == raw, "note was trimmed or normalised"


def test_note_length_boundaries(world):
    r = _pay(world.ada, 10, note="n" * 200)
    assert_status(r, 201)
    r = _pay(world.ada, 10, note="n" * 201)
    assert_error(r, 422, "validation_failed")
    r = _pay(world.ada, 10, note=None)
    assert_error(r, 422, "validation_failed")
    r = _pay(world.ada, 10, note=5)
    assert_error(r, 422, "validation_failed")


def test_amount_accepts_only_integral_numeric_forms(world):
    for good in (1000, 1000.0, 1e3):
        r = _pay(world.ada, good, to_handle="bob")
        assert_status(r, 201)
    for bad in ("1000", True, False, None):
        r = _pay(world.ada, bad, to_handle="bob")
        assert_error(r, 422, "validation_failed")


def test_amount_out_of_range_is_rejected(world):
    for bad in (0, -1, 1_000_000_001):
        r = _pay(world.ada, bad, to_handle="bob")
        assert_error(r, 422, "validation_failed")


def test_max_amount_moves_exactly(boot):
    w = boot(fixture(users=[user("ada", 1_000_000_000), user("bob", 0)]),
             handles=("ada", "bob"))
    r = _pay(w.ada, 1_000_000_000)
    assert_status(r, 201)
    assert w.ada.balance() == 0
    assert w.bob.balance() == 1_000_000_000


def test_arithmetic_near_two_pow_53_is_exact(boot):
    big = 2 ** 53 - 1
    w = boot(fixture(users=[user("ada", big), user("bob", 0)]), handles=("ada", "bob"))
    assert_status(_pay(w.ada, 1), 201)
    assert w.ada.balance() == big - 1
    assert w.bob.balance() == 1
    assert w.ada.balance() + w.bob.balance() == w.total


def test_self_and_unknown_handles(world):
    r = _pay(world.ada, 10, to_handle="ada")
    assert_error(r, 422, "self_payment")
    r = _pay(world.ada, 10, to_handle="ghost")
    assert_error(r, 404, "not_found")
    r = _request(world.bob, 10, payer_handle="bob")
    assert_error(r, 422, "self_request")
    r = _request(world.bob, 10, payer_handle="ghost")
    assert_error(r, 404, "not_found")


def test_minor_units_from_fixture_are_reported(boot):
    for currency, units in (("JPY", 0), ("EUR", 2), ("BHD", 3)):
        w = boot(fixture(users=[user("ada", 1000), user("bob", 0)], currency=currency),
                 handles=("ada", "bob"))
        me = w.ada.me()
        assert me["minor_units"] == units, me
        assert me["currency"] == currency, me


def test_conservation_after_a_mixed_sequence(world):
    assert_status(_pay(world.ada, 100, to_handle="bob"), 201)
    assert_status(_pay(world.bob, 50, to_handle="cy"), 201)
    assert_status(_request(world.cy, 25, payer_handle="ada"), 201)
    assert_status(_pay(world.ada, 1, to_handle="cy"), 201)
    total = sum(c.balance() for c in world.all)
    assert total == world.total, f"ledger drifted: {total} != {world.total}"
