"""S3-R14..R19, R25, R27: corrections, revisions, error codes and atomicity."""
from __future__ import annotations

from attacklib3 import (
    assert_error,
    assert_status,
    authz,
    correction_body,
    fixture3,
    future_iso,
    minus,
    new_key,
    parse_ts,
    payment_seed,
    plus,
    revision_list,
)

PASSWORD = "correct horse"


def _users(ada=100000, bob=500, cy=250, op=100000):
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


def _pay(client, to_handle, amount, *, key=None):
    return client.post("/payments", json={"to_handle": to_handle, "amount": amount},
                       headers={"Idempotency-Key": key or new_key()})


def _make_payment(world, amount=100):
    return assert_status(_pay(world.ada, "bob", amount), 201).json()


def _valid_body(made, amount=400):
    return correction_body(1, amount, made["created_at"], "corrected amount")


def test_non_sender_is_403_and_unknown_is_404(world3):
    made = _make_payment(world3)
    assert_error(world3.bob.correct(made["payment_id"], _valid_body(made)), 403, "forbidden")
    assert_error(world3.ada.correct("p_missing", _valid_body(made)), 404, "not_found")


def test_correction_body_validation_table(world3):
    made = _make_payment(world3)
    pid = made["payment_id"]
    base = _valid_body(made)
    cases = [
        {},
        {k: v for k, v in base.items() if k != "expected_revision"},
        {k: v for k, v in base.items() if k != "amount"},
        {k: v for k, v in base.items() if k != "effective_at"},
        {k: v for k, v in base.items() if k != "reason"},
        {**base, "expected_revision": 0},
        {**base, "expected_revision": -1},
        {**base, "expected_revision": 1.5},
        {**base, "expected_revision": "1"},
        {**base, "amount": -1},
        {**base, "amount": 1_000_000_001},
        {**base, "amount": 1.5},
        {**base, "amount": "100"},
        {**base, "reason": ""},
        {**base, "reason": "x" * 201},
        {**base, "effective_at": plus(3600)},
        {**base, "effective_at": "2026-09-24T08:00:00"},
    ]
    for body in cases:
        resp = world3.ada.correct(pid, body)
        assert resp.status_code == 422, \
            f"body {body!r} must be 422 validation_failed, got {resp.status_code}"
        assert resp.json().get("error", {}).get("code") == "validation_failed", resp.text


def test_replay_is_200_identical_and_key_reuse_is_409(world3):
    made = _make_payment(world3)
    pid = made["payment_id"]
    key = new_key()
    first = assert_status(world3.ada.correct(pid, _valid_body(made), key=key), 201).json()
    replay = world3.ada.correct(pid, _valid_body(made), key=key)
    assert replay.status_code == 200
    assert replay.json() == first, "replaying a correction must return the original body"

    reused = world3.ada.correct(pid, {
        "expected_revision": 2, "amount": 300,
        "effective_at": made["created_at"], "reason": "different"}, key=key)
    assert_error(reused, 409, "idempotency_key_reuse")

    assert len(revision_list(world3.ada.revisions(pid))) == 2, \
        "a replayed correction must not append another revision"


def test_stale_revision_is_409_and_recorded_times_increase(world3):
    made = _make_payment(world3)
    pid = made["payment_id"]
    first = assert_status(world3.ada.correct(pid, _valid_body(made, 400)), 201).json()
    stale = world3.ada.correct(pid, correction_body(1, 300, made["created_at"], "stale"))
    assert_error(stale, 409, "stale_revision")

    second = assert_status(world3.ada.correct(
        pid, correction_body(2, 350, made["created_at"], "second")), 201).json()
    assert parse_ts(second["recorded_at"]) > parse_ts(first["recorded_at"]), \
        "recorded_at must strictly increase per payment"
    assert second["revision"] == 3


def test_correction_moves_money_between_same_wallets_and_preserves_total(world3):
    before_total = sum(c.me_full()["balance"] for c in world3.all)
    ada_before = world3.ada.balance()
    bob_before = world3.bob.balance()
    made = _make_payment(world3, 100)
    assert_status(world3.ada.correct(made["payment_id"], _valid_body(made, 400)), 201)
    assert world3.ada.balance() == ada_before - 100 - 300, \
        "increasing the amount debits the original sender by the difference"
    assert world3.bob.balance() == bob_before + 100 + 300
    assert sum(c.me_full()["balance"] for c in world3.all) == before_total

    reversed_ = assert_status(
        world3.ada.correct(made["payment_id"], correction_body(2, 0, made["created_at"], "reverse")),
        201).json()
    assert world3.ada.balance() == ada_before, "a zero revision reverses the whole payment"
    assert reversed_["amount"] == 0


def test_unaffordable_increase_is_insufficient_funds_and_preserves_state(world3):
    made = _make_payment(world3, 100)
    pid = made["payment_id"]
    ada_before = world3.ada.balance()
    resp = world3.ada.correct(pid, _valid_body(made, 10_000_000))
    assert_error(resp, 409, "insufficient_funds")
    assert world3.ada.balance() == ada_before, "a failed correction must not move money"
    assert len(revision_list(world3.ada.revisions(pid))) == 1, \
        "a failed correction must not append a revision"


def test_past_boundary_overdraft_is_historical_overdraft(boot3):
    world = boot3(fixture3(users=_users(1000, 0), operators=[], payments=[
        payment_seed("p1", "u_ada", "u_bob", 900, created_at="2026-09-24T06:00:00+00:00"),
        payment_seed("p2", "u_bob", "u_ada", 900, created_at="2026-09-24T07:00:00+00:00"),
    ]))
    pid = "p1"
    # current balance is 1000, so an increase of 600 is affordable now, but at t1 ada
    # would have held 1000-1500 = -500.
    resp = world.ada.correct(pid, correction_body(1, 1500, "2026-09-24T06:00:00+00:00", "overdraft"))
    assert_error(resp, 409, "historical_overdraft")
    assert world.ada.me_full()["balance"] == 1000, "state must be preserved"
    assert len(revision_list(world.ada.revisions(pid))) == 1


def test_revisions_are_party_only_ordered_with_empty_rev1_reason(world3):
    made = _make_payment(world3, 100)
    pid = made["payment_id"]
    assert_status(world3.ada.correct(pid, _valid_body(made, 400)), 201)
    revs = revision_list(assert_status(world3.ada.revisions(pid), 200))
    assert [r["revision"] for r in revs] == [1, 2], f"revisions must be ordered: {revs}"
    assert revs[0]["reason"] == "", "revision 1 must carry an empty reason"
    assert revs[1]["reason"] == "corrected amount"
    assert_status(world3.bob.revisions(pid), 200)  # receiver is a party
    assert_error(world3.cy.revisions(pid), 404, "not_found")


def test_activity_shows_original_payment_only(world3):
    made = _make_payment(world3, 100)
    pid = made["payment_id"]
    before = world3.ada.get("/activity").json()["payments"]
    assert_status(world3.ada.correct(pid, _valid_body(made, 400)), 201)
    after = world3.ada.get("/activity").json()["payments"]
    assert len(after) == len(before), "a correction must not add a feed item"
    assert after[0]["payment_id"] == pid
    assert after[0]["visibility"] == before[0]["visibility"]


def test_capture_correction_is_linked_payment_immutable(boot3):
    world = boot3(fixture3(users=_users(1000, 0), operators=[], authorizations=[
        authz("a_seed", "u_ada", "u_bob", 300, expires_at=future_iso(7200)),
    ]))
    captured = assert_status(world.bob.capture("a_seed", amount=300), 201).json()
    resp = world.ada.correct(captured["payment_id"],
                             correction_body(1, 100, captured["created_at"], "x"))
    assert_error(resp, 422, "linked_payment_immutable")


def test_settlement_member_correction_is_linked_payment_immutable(boot3):
    world = boot3(fixture3(users=_users(1000, 0, 0, 1000), operators=["u_op"]))
    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 100}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    member = settled["payments"][0]
    resp = world.ada.correct(member["payment_id"],
                             correction_body(1, 50, member["created_at"], "x"))
    assert_error(resp, 422, "linked_payment_immutable")
