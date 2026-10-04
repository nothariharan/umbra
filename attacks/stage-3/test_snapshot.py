"""S3-R22, R23, R28: snapshot pagination, stability under writes, token errors."""
from __future__ import annotations

from attacklib3 import (
    assert_error,
    assert_status,
    entries_of,
    fixture3,
    new_key,
    payment_seed,
    race,
)

PASSWORD = "correct horse"


def _users(ada=1000, bob=500):
    return [
        {"id": "u_ada", "email": "ada@example.com", "password": PASSWORD,
         "display_name": "Ada", "handle": "ada", "balance": ada},
        {"id": "u_bob", "email": "bob@example.com", "password": PASSWORD,
         "display_name": "Bob", "handle": "bob", "balance": bob},
    ]


def _world(boot3):
    return boot3(fixture3(users=_users(), operators=[], payments=[
        payment_seed("p1", "u_bob", "u_ada", 200, created_at="2026-09-24T06:00:00+00:00"),
        payment_seed("p2", "u_ada", "u_bob", 100, created_at="2026-09-24T07:00:00+00:00"),
        payment_seed("p3", "u_bob", "u_ada", 50, created_at="2026-09-24T08:00:00+00:00"),
    ]))


def _snapshot(world):
    body = assert_status(world.ada.statement(limit=50), 200).json()
    token = body.get("snapshot")
    assert isinstance(token, str) and token, f"first statement must return a snapshot token: {body}"
    return body, token


def test_snapshot_paging_freezes_entries_and_balances(boot3):
    world = _world(boot3)
    whole, token = _snapshot(world)
    page = assert_status(world.ada.statement(snapshot=token, limit=1, offset=1), 200).json()
    full = {e["payment"]["payment_id"]: e for e in whole["entries"]}
    assert [e["payment"]["payment_id"] for e in entries_of(
        world.ada.statement(snapshot=token, limit=1, offset=1))] == ["p2"]
    assert page["opening_balance"] == whole["opening_balance"]
    assert page["closing_balance"] == whole["closing_balance"]
    assert page["entries"][0]["balance_after"] == full["p2"]["balance_after"]


def test_snapshot_with_window_params_is_422(world3):
    token = _snapshot(world3)[1]
    for params in ({"snapshot": token, "from": "2026-09-24T00:00:00+00:00"},
                   {"snapshot": token, "to": "2026-09-25T00:00:00+00:00"},
                   {"snapshot": token, "known_at": "2026-09-24T00:00:00+00:00"}):
        resp = world3.ada.statement(**params)
        assert resp.status_code == 422, f"{params} with snapshot must be 422"
        assert resp.json().get("error", {}).get("code") == "validation_failed"


def test_snapshot_bad_wrong_user_and_pre_reset_tokens_are_404(world3, reset):
    token = _snapshot(world3)[1]
    assert_error(world3.ada.statement(snapshot="not-a-real-token"), 404, "not_found")
    assert_error(world3.bob.statement(snapshot=token), 404, "not_found")
    reset(fixture3())
    assert_error(world3.ada.statement(snapshot=token), 404, "not_found")


def test_snapshot_is_stable_through_concurrent_writes(boot3):
    world = _world(boot3)
    before, token = _snapshot(world)
    for i in range(5):
        assert_status(world.ada.post(
            "/payments", json={"to_handle": "bob", "amount": 10},
            headers={"Idempotency-Key": new_key()}), 201)
    after = assert_status(world.ada.statement(snapshot=token, limit=50), 200).json()
    assert after["opening_balance"] == before["opening_balance"]
    assert after["closing_balance"] == before["closing_balance"]
    assert [e["payment"]["payment_id"] for e in after["entries"]] == \
        [e["payment"]["payment_id"] for e in before["entries"]], \
        "existing snapshots must not absorb later writes"


def test_concurrent_same_revision_corrections_cannot_both_succeed(world3):
    made = assert_status(world3.ada.post(
        "/payments", json={"to_handle": "bob", "amount": 100},
        headers={"Idempotency-Key": new_key()}), 201).json()
    pid = made["payment_id"]

    def attempt(i):
        return world3.ada.correct(pid, {
            "expected_revision": 1, "amount": 200 + i,
            "effective_at": made["created_at"], "reason": f"correction {i}"})

    results = race(attempt, 2)
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409], f"exactly one concurrent correction may win, got {codes}"
    loser = next(r for r in results if r.status_code == 409)
    assert loser.json().get("error", {}).get("code") == "stale_revision", loser.text
    assert world3.ada.revisions(pid).json() is not None
