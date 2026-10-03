"""Repetition and ordering attacks on the five idempotent write paths.

A repeated, reordered or partially failed request must not change the outcome
twice; a key reused with a different body must not silently take effect.
"""
from __future__ import annotations

from attacklib import assert_error, assert_status, new_key

PAY = "/payments"
REQ = "/requests"
SPLIT = "/splits"
SETTLE = "/settlements"


def _pay(client, amount=100, *, to_handle="bob", key=None, **extra):
    body = {"to_handle": to_handle, "amount": amount}
    body.update(extra)
    headers = {} if key is None else {"Idempotency-Key": key}
    return client.post(PAY, json=body, headers=headers)


def test_missing_or_empty_key_is_400(world):
    for headers in ({}, {"Idempotency-Key": ""}):
        r = world.ada.post(PAY, json={"to_handle": "bob", "amount": 100},
                           headers=headers)
        assert_error(r, 400, "missing_idempotency_key")
    r = world.bob.post(REQ, json={"payer_handle": "ada", "amount": 100}, headers={})
    assert_error(r, 400, "missing_idempotency_key")


def test_key_length_boundaries(world):
    one = "a" * 1
    maxik = "b" * 255
    too_long = "c" * 256
    r = _pay(world.ada, key=one)
    assert_status(r, 201)
    r = _pay(world.ada, key=maxik)
    assert_status(r, 201)
    r = _pay(world.ada, key=too_long)
    assert_error(r, 422, "validation_failed")


def test_replay_returns_identical_body_without_second_effect(world):
    key = new_key()
    first = _pay(world.ada, 100, key=key)
    assert_status(first, 201)
    before = world.ada.balance()
    replay = _pay(world.ada, 100, key=key)
    assert_status(replay, 200)
    assert replay.json() == first.json(), "replay body differs from the original"
    assert world.ada.balance() == before, "a replay moved money again"


def test_same_key_different_body_is_reuse(world):
    key = new_key()
    assert_status(_pay(world.ada, 100, to_handle="bob", key=key), 201)
    r = _pay(world.ada, 100, to_handle="cy", key=key)
    assert_error(r, 409, "idempotency_key_reuse")


def test_key_reusable_after_a_4xx_failure(world):
    key = new_key()
    bad = _pay(world.ada, 0, key=key)
    assert_error(bad, 422, "validation_failed")
    good = _pay(world.ada, 100, key=key)
    assert_status(good, 201)


def test_claimed_key_wins_over_invalid_body(world):
    key = new_key()
    assert_status(_pay(world.ada, 100, key=key), 201)
    r = _pay(world.ada, 0, key=key)
    assert_error(r, 409, "idempotency_key_reuse")


def test_same_key_different_path_is_not_a_replay(world):
    key = new_key()
    p = _pay(world.ada, 100, key=key)
    assert_status(p, 201)
    q = world.bob.post(REQ, json={"payer_handle": "ada", "amount": 100},
                       headers={"Idempotency-Key": key})
    assert_status(q, 201)


def test_key_is_scoped_to_the_authenticated_user(world):
    key = new_key()
    a = _pay(world.ada, 100, key=key)
    b = _pay(world.bob, 100, to_handle="cy", key=key)
    assert_status(a, 201)
    assert_status(b, 201)
    assert a.json()["payment_id"] != b.json()["payment_id"]


def test_request_pay_replay_after_paid_returns_200(world):
    made = world.bob.post(REQ, json={"payer_handle": "ada", "amount": 100},
                          headers={"Idempotency-Key": new_key()})
    assert_status(made, 201)
    rid = made.json()["request_id"]
    key = new_key()
    first = world.ada.post(f"/requests/{rid}/pay", json={},
                           headers={"Idempotency-Key": key})
    assert_status(first, 201)
    assert first.json()["request_id"] == rid
    replay = world.ada.post(f"/requests/{rid}/pay", json={},
                            headers={"Idempotency-Key": key})
    assert_status(replay, 200)
    assert replay.json() == first.json()
    blocked = world.ada.post(f"/requests/{rid}/pay", json={},
                             headers={"Idempotency-Key": new_key()})
    assert_error(blocked, 409, "request_not_pending")


def test_decline_twice_is_200(world):
    made = world.bob.post(REQ, json={"payer_handle": "ada", "amount": 100},
                          headers={"Idempotency-Key": new_key()})
    rid = made.json()["request_id"]
    first = world.ada.post(f"/requests/{rid}/decline")
    assert_status(first, 200)
    second = world.ada.post(f"/requests/{rid}/decline")
    assert_status(second, 200)
    assert second.json()["status"] == "declined"


def test_cancel_twice_is_200(world):
    made = world.bob.post(REQ, json={"payer_handle": "ada", "amount": 100},
                          headers={"Idempotency-Key": new_key()})
    rid = made.json()["request_id"]
    assert_status(world.bob.post(f"/requests/{rid}/cancel"), 200)
    second = world.bob.post(f"/requests/{rid}/cancel")
    assert_status(second, 200)
    assert second.json()["status"] == "cancelled"


def test_split_replay_is_identical_and_creates_nothing_extra(world):
    key = new_key()
    body = {"amount": 300, "participant_handles": ["ada", "bob", "cy"], "note": "x"}
    first = world.ada.post(SPLIT, json=body, headers={"Idempotency-Key": key})
    assert_status(first, 201)
    count = len(world.bob.get(REQ).json()["requests"])
    replay = world.ada.post(SPLIT, json=body, headers={"Idempotency-Key": key})
    assert_status(replay, 200)
    assert replay.json() == first.json()
    assert len(world.bob.get(REQ).json()["requests"]) == count, "replay duplicated requests"


def test_settlement_replay_is_identical_and_moves_nothing_extra(world):
    key = new_key()
    body = {"transfers": [{"from_handle": "op", "to_handle": "bob", "amount": 300}]}
    first = world.op.post(SETTLE, json=body, headers={"Idempotency-Key": key})
    assert_status(first, 201)
    op_after = world.op.balance()
    bob_after = world.bob.balance()
    replay = world.op.post(SETTLE, json=body, headers={"Idempotency-Key": key})
    assert_status(replay, 200)
    assert replay.json() == first.json()
    assert world.op.balance() == op_after
    assert world.bob.balance() == bob_after
