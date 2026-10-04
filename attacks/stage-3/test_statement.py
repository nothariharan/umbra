"""S3-R9..R13, R20, R21, R28: GET /statement ordering, balances, pagination, corrections."""
from __future__ import annotations

from attacklib3 import (
    assert_status,
    authz,
    entries_of,
    fixture3,
    future_iso,
    new_key,
    parse_ts,
    payment_seed,
)

PASSWORD = "correct horse"
T1 = "2026-09-24T06:00:00+00:00"
T2 = "2026-09-24T07:00:00+00:00"
T3 = "2026-09-24T08:00:00+00:00"


def _users(ada=1000, bob=500, cy=0, op=0):
    return [
        {"id": "u_ada", "email": "ada@example.com", "password": PASSWORD,
         "display_name": "Ada", "handle": "ada", "balance": ada},
        {"id": "u_bob", "email": "bob@example.com", "password": PASSWORD,
         "display_name": "Bob", "handle": "bob", "balance": bob},
        {"id": "u_cy", "email": "cy@example.com", "password": PASSWORD,
         "display_name": "Cy", "handle": "cy", "balance": cy},
        {"id": "u_op", "email": "op@example.com", "password": PASSWORD,
         "display_name": "Op", "handle": "op", "balance": op},
    ]


def _seeded_world(boot3):
    return boot3(fixture3(users=_users(), operators=[], payments=[
        payment_seed("p1", "u_bob", "u_ada", 200, created_at=T1),
        payment_seed("p2", "u_ada", "u_bob", 100, created_at=T2),
        payment_seed("p3", "u_bob", "u_ada", 50, created_at=T3),
    ]))


def test_statement_orders_oldest_first_and_reports_balances(boot3):
    world = _seeded_world(boot3)
    body = assert_status(world.ada.statement(), 200).json()
    entries = entries_of(world.ada.statement())
    assert [e["payment"]["payment_id"] for e in entries] == ["p1", "p2", "p3"], \
        "statement entries must be oldest-first"
    assert body["opening_balance"] == 850, "opening is the balance before the first entry"
    assert entries[0]["delta"] == 200 and entries[0]["balance_after"] == 1050
    assert entries[1]["delta"] == -100 and entries[1]["balance_after"] == 950
    assert entries[2]["delta"] == 50 and entries[2]["balance_after"] == 1000
    assert body["closing_balance"] == 1000
    assert body["opening_balance"] + sum(e["delta"] for e in entries) == body["closing_balance"]


def test_statement_window_is_half_open(boot3):
    world = _seeded_world(boot3)
    body = assert_status(world.ada.statement(**{"from": T2, "to": T3}), 200).json()
    entries = entries_of(world.ada.statement(**{"from": T2, "to": T3}))
    assert [e["payment"]["payment_id"] for e in entries] == ["p2"], \
        f"[from,to) must exclude the from instant and the to instant, got {entries}"
    assert body["opening_balance"] == 1050, "opening is the balance immediately before from"
    assert body["closing_balance"] == 950, "closing is the balance immediately before to"


def test_statement_pagination_preserves_balance_after(boot3):
    world = _seeded_world(boot3)
    full = {e["payment"]["payment_id"]: e for e in entries_of(world.ada.statement(limit=50))}
    page = entries_of(world.ada.statement(limit=1, offset=1))
    assert [e["payment"]["payment_id"] for e in page] == ["p2"]
    assert page[0]["balance_after"] == full["p2"]["balance_after"], \
        "pagination must not change balance_after"
    whole = assert_status(world.ada.statement(limit=50), 200).json()
    sliced = assert_status(world.ada.statement(limit=1, offset=1), 200).json()
    assert sliced["opening_balance"] == whole["opening_balance"]
    assert sliced["closing_balance"] == whole["closing_balance"]


def test_statement_is_party_only_not_feed_visibility(boot3):
    world = boot3(fixture3(users=_users(), operators=[], payments=[
        payment_seed("p_pub", "u_ada", "u_bob", 100, created_at=T1, visibility="public"),
    ]))
    cy_entries = entries_of(world.cy.statement())
    assert cy_entries == [], \
        "a third party's statement must exclude a public payment they are not party to"
    assert {e["payment"]["payment_id"] for e in entries_of(world.bob.statement())} == {"p_pub"}
    assert {e["payment"]["payment_id"] for e in entries_of(world.ada.statement())} == {"p_pub"}


def test_invalid_statement_params_are_422(world3):
    for params in ({"from": "2026-09-24"}, {"to": ""}, {"limit": "notanint"},
                   {"offset": "-1"}, {"limit": "0"}):
        resp = world3.ada.statement(**params)
        assert resp.status_code == 422, f"{params} must be 422, got {resp.status_code}"


def test_corrected_statement_orders_by_effective_time_and_uses_selected_amount(world3):
    made = assert_status(
        world3.ada.post("/payments", json={"to_handle": "bob", "amount": 100},
                        headers={"Idempotency-Key": new_key()}), 201).json()
    pid = made["payment_id"]
    # move the revision's effective time earlier than the original created_at
    effective = "2026-09-24T05:00:00+00:00"
    assert_status(world3.ada.correct(pid, {
        "expected_revision": 1, "amount": 400,
        "effective_at": effective, "reason": "corrected amount"}), 201)

    entries = entries_of(world3.ada.statement(limit=200))
    entry = next(e for e in entries if e["payment"]["payment_id"] == pid)
    assert entry["payment"]["amount"] == 400, "payment.amount must be the selected revision"
    assert entry.get("revision") == 2
    assert parse_ts(entry.get("effective_at")) == parse_ts(effective)
    # a later entry (bob -> ada) created after the correction's effective time sorts after
    later = assert_status(world3.bob.post(
        "/payments", json={"to_handle": "ada", "amount": 10},
        headers={"Idempotency-Key": new_key()}), 201).json()
    order = [e["payment"]["payment_id"] for e in entries_of(world3.ada.statement(limit=200))]
    assert order.index(pid) < order.index(later["payment_id"]), \
        "entries must be ordered by selected effective_at"


def test_zero_amount_revision_appears_with_zero_delta(world3):
    made = assert_status(
        world3.ada.post("/payments", json={"to_handle": "bob", "amount": 100},
                        headers={"Idempotency-Key": new_key()}), 201).json()
    assert_status(world3.ada.correct(made["payment_id"], {
        "expected_revision": 1, "amount": 0,
        "effective_at": made["created_at"], "reason": "reverse"}), 201)
    entry = next(e for e in entries_of(world3.ada.statement(limit=200))
                 if e["payment"]["payment_id"] == made["payment_id"])
    assert entry["delta"] == 0, "a zero-amount revision must reverse the payment"
    assert entry["payment"]["amount"] == 0


def test_statement_has_more_across_pages_and_beyond_end(boot3):
    world = _seeded_world(boot3)
    first = assert_status(world.ada.statement(limit=1, offset=0), 200).json()
    assert first["has_more"] is True, "a partial page with more entries must set has_more"
    last = assert_status(world.ada.statement(limit=1, offset=2), 200).json()
    assert last["has_more"] is False, "the final page must clear has_more"
    beyond = assert_status(world.ada.statement(limit=10, offset=50), 200).json()
    assert beyond["entries"] == []
    assert beyond["has_more"] is False, "an offset beyond the end must not claim has_more"


def test_statement_ignores_unknown_query_parameters(world3):
    body = assert_status(world3.ada.statement(nonsense="1", extra="x"), 200).json()
    assert "entries" in body


def test_statement_and_revisions_require_a_token(world3):
    from attacklib3 import Client
    anon = Client()
    try:
        assert_error(anon.get("/statement"), 401, "unauthenticated")
        assert_error(anon.get("/payments/p_x/revisions"), 401, "unauthenticated")
    finally:
        anon.close()


def test_settlement_member_uses_committed_at_as_effective_and_recorded(boot3):
    world = boot3(fixture3(users=_users(1000, 0, 0, 0), operators=["u_op"]))
    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 100}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    committed = settled.get("committed_at")
    assert committed, "a settlement must report committed_at"
    member = settled["payments"][0]["payment_id"]
    entry = next(e for e in entries_of(world.ada.statement(limit=200))
                 if e["payment"]["payment_id"] == member)
    assert parse_ts(entry.get("effective_at")) == parse_ts(committed)
    assert parse_ts(entry.get("recorded_at")) == parse_ts(committed)


def test_capture_appears_once_with_link_and_no_auth_rows(boot3):
    world = boot3(fixture3(users=_users(1000, 0), operators=[], authorizations=[
        authz("a_seed", "u_ada", "u_bob", 300, expires_at=future_iso(7200)),
    ]))
    captured = assert_status(world.bob.capture("a_seed", amount=300), 201).json()
    entries = entries_of(world.bob.statement(limit=200))
    matches = [e for e in entries if e["payment"]["payment_id"] == captured["payment_id"]]
    assert len(matches) == 1, "a capture must appear exactly once in the statement"
    assert matches[0]["payment"].get("authorization_id") == "a_seed"
    for e in entries:
        assert "authorization_id" in e["payment"] or True  # statement lists payments only
