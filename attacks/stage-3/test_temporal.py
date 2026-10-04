"""S3-R6..R8, R20, R26: temporal GET /me (as_of, known_at) and historical holds."""
from __future__ import annotations

from attacklib3 import (
    assert_error,
    assert_status,
    authz,
    fixture3,
    future_iso,
    minus,
    new_key,
    payment_seed,
    plus,
)

PASSWORD = "correct horse"


def _users(balance_ada=1000, balance_bob=0):
    return [
        {"id": "u_ada", "email": "ada@example.com", "password": PASSWORD,
         "display_name": "Ada", "handle": "ada", "balance": balance_ada},
        {"id": "u_bob", "email": "bob@example.com", "password": PASSWORD,
         "display_name": "Bob", "handle": "bob", "balance": balance_bob},
    ]


def test_invalid_as_of_forms_are_422(world3):
    for bad in ("2026-09-24T08:00:00", "2026-09-24", "", "not-a-time", "1700000000"):
        resp = world3.ada.me_at(as_of=bad)
        assert resp.status_code == 422, f"as_of={bad!r} must be 422, got {resp.status_code}"
        assert resp.json().get("error", {}).get("code") == "validation_failed", resp.text


def test_as_of_edges_before_earliest_exact_and_after_latest(boot3):
    created = minus(7200)
    world = boot3(fixture3(users=_users(), operators=[], payments=[
        payment_seed("p_seed", "u_ada", "u_bob", 400, created_at=created),
    ]))
    current = assert_status(world.ada.me_at(), 200).json()
    assert current["balance"] == 1000, "current balance is the fixture balance"

    before = assert_status(world.ada.me_at(as_of=minus(7200 + 3600)), 200).json()
    assert before["balance"] == 1400, \
        "before the earliest payment the balance is the opening balance (1000 + 400 sent)"

    at = assert_status(world.ada.me_at(as_of=created), 200).json()
    assert at["balance"] == 1000, "a payment made exactly at as_of counts"

    after = assert_status(world.ada.me_at(as_of=plus(60)), 200).json()
    assert after["balance"] == 1000, "at or after the latest payment returns the current balance"


def test_as_of_is_echoed_exactly(world3):
    given = "2026-09-24T13:20:00+02:00"
    resp = assert_status(world3.ada.me_at(as_of=given), 200)
    assert resp.json().get("as_of") == given, \
        f"as_of must be echoed exactly as given, got {resp.json().get('as_of')!r}"


def test_known_at_selects_revision_and_echoes(world3):
    made = assert_status(
        world3.ada.post("/payments", json={"to_handle": "bob", "amount": 100},
                        headers={"Idempotency-Key": new_key()}), 201).json()
    pid = made["payment_id"]
    corrected = assert_status(
        world3.ada.correct(pid, {"expected_revision": 1, "amount": 400,
                                 "effective_at": made["created_at"],
                                 "reason": "correct amount"}), 201).json()
    recorded = corrected["recorded_at"]

    now_view = assert_status(world3.ada.me_at(known_at=plus(1)), 200).json()
    assert now_view["balance"] == 100000 - 400, "latest revision must be applied"

    past_view = assert_status(world3.ada.me_at(known_at=made["created_at"]), 200).json()
    assert past_view["balance"] == 100000 - 100, \
        "a known_at before the correction recorded_at selects revision 1"
    assert past_view.get("known_at") == made["created_at"]
    assert recorded  # server assigned a recorded time


def test_historical_hold_totals_are_consistent(boot3):
    world = boot3(fixture3(users=_users(1000, 0), operators=[], authorizations=[
        authz("a_seed", "u_ada", "u_bob", 300, expires_at=future_iso(7200)),
    ]))
    view = assert_status(world.ada.me_at(as_of=plus(60), known_at=plus(60)), 200).json()
    assert view["balance"] == view.get("total", view["balance"])
    assert view["available"] == view["total"] - view["held"]
    assert view["held"] == 300, "a seeded open hold must be visible in the historical view"
    assert view["available"] == 700


def test_bad_known_at_is_422(world3):
    resp = world3.ada.me_at(known_at="2026-09-24")
    assert resp.status_code == 422
    assert resp.json().get("error", {}).get("code") == "validation_failed"


def test_correction_known_at_not_yet_recorded_omits_payment(boot3):
    # A payment created after known_at must be omitted from the historical view.
    world = boot3(fixture3(users=_users(), operators=[]))
    assert_status(world.ada.post("/payments",
                                 json={"to_handle": "bob", "amount": 100},
                                 headers={"Idempotency-Key": new_key()}), 201)
    opening = assert_status(world.ada.me_at(as_of=minus(7200), known_at=minus(7200)), 200)
    assert opening.json()["balance"] == 1000, \
        "a payment recorded after known_at must not affect a known_at view"


def test_future_query_instants_are_allowed(world3):
    as_of = plus(3600)
    known_at = plus(7200)
    view = world3.ada.me_at(as_of=as_of, known_at=known_at)
    assert view.status_code == 200, "future as_of/known_at must be accepted, not 422"
    body = view.json()
    assert body["balance"] == 100000, "a future read returns the current balance"
    assert body.get("as_of") == as_of
    assert body.get("known_at") == known_at


def test_known_at_is_echoed_exactly(world3):
    given = "2026-09-24T13:20:00+02:00"
    body = assert_status(world3.ada.me_at(known_at=given), 200).json()
    assert body.get("known_at") == given, \
        f"known_at must be echoed exactly, got {body.get('known_at')!r}"


def test_authorization_closed_at_tracks_lifecycle(boot3):
    world = boot3(fixture3(users=_users(1000, 0), operators=[], authorizations=[
        authz("a_seed", "u_ada", "u_bob", 300, expires_at=future_iso(7200)),
    ]))
    listing = assert_status(world.ada.list_authorizations(limit=50), 200).json()
    items = listing.get("authorizations") if isinstance(listing, dict) else listing
    item = next(a for a in items if (a.get("authorization_id") or a.get("id")) == "a_seed")
    assert "closed_at" in item, "authorizations must expose closed_at"
    assert item["closed_at"] is None, "an open authorization must have closed_at null"

    assert_status(world.ada.void("a_seed"), 200)
    listing = assert_status(world.ada.list_authorizations(limit=50), 200).json()
    items = listing.get("authorizations") if isinstance(listing, dict) else listing
    item = next(a for a in items if (a.get("authorization_id") or a.get("id")) == "a_seed")
    assert item["closed_at"] is not None, "a closed authorization must carry its event time"
    from attacklib3 import parse_ts
    parse_ts(item["closed_at"])
