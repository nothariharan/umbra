"""S4-R22, R23: batch success shape, shared recorded_at, statements, snapshots, replay."""
from __future__ import annotations

from attacklib4 import (
    assert_error,
    assert_status,
    batch_item,
    entries_of,
    fixture3,
    new_key,
    parse_ts,
    plus,
    revisions_of,
)

PASSWORD = "correct horse"


def _users(ada=100000, bob=1000, cy=1000, op=100000):
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


def _world(boot4):
    return boot4(fixture3(users=_users(), operators=["u_op"]))


def _pay(world, to_handle, amount, key=None):
    k = key or new_key()
    resp = assert_status(world.ada.post(
        "/payments", json={"to_handle": to_handle, "amount": amount},
        headers={"Idempotency-Key": k}), 201)
    return resp, k


def test_batch_success_shape_shared_recorded_at_and_order(boot4):
    world = _world(boot4)
    p1, _ = _pay(world, "bob", 100)
    p2, _ = _pay(world, "cy", 100)
    a, b = p1.json(), p2.json()
    prior1 = parse_ts(revisions_of(world.ada.revisions(a["payment_id"]))[0]["recorded_at"])
    prior2 = parse_ts(revisions_of(world.ada.revisions(b["payment_id"]))[0]["recorded_at"])

    body = [batch_item(a["payment_id"], 1, 70, a["created_at"]),
            batch_item(b["payment_id"], 1, 30, b["created_at"])]
    resp = assert_status(world.op.batch(body), 201)
    out = resp.json()
    assert isinstance(out.get("correction_batch_id"), str) and out["correction_batch_id"], \
        f"a batch response must carry correction_batch_id: {out}"
    recorded = parse_ts(out["recorded_at"])
    assert recorded > prior1 and recorded > prior2, \
        "the shared recorded_at must be strictly after every prior recorded_at"
    revs = out["revisions"]
    assert [r["payment_id"] for r in revs] == [a["payment_id"], b["payment_id"]], \
        f"revisions must be in input order: {revs}"
    for r in revs:
        assert r.get("correction_batch_id") == out["correction_batch_id"], \
            "each revision must expose correction_batch_id"
        assert parse_ts(r["recorded_at"]) == recorded, "all revisions share one recorded_at"
    # revisions endpoint exposes the batch link too
    listing = revisions_of(world.ada.revisions(a["payment_id"]))
    assert listing[-1].get("correction_batch_id") == out["correction_batch_id"]


def test_statements_reflect_new_revisions_and_originals_retry_unchanged(boot4):
    world = _world(boot4)
    p1, key1 = _pay(world, "bob", 100)
    a = p1.json()
    assert_status(world.op.batch([batch_item(a["payment_id"], 1, 25, a["created_at"])]), 201)
    entries = {e["payment"]["payment_id"]: e for e in
               entries_of(world.ada.statement(limit=200))}
    assert entries[a["payment_id"]]["payment"]["amount"] == 25, \
        "the statement must show the new revision"
    # replaying the original payment creation returns the original body, unchanged
    replay = world.ada.post("/payments", json={"to_handle": "bob", "amount": 100},
                            headers={"Idempotency-Key": key1})
    assert replay.status_code == 200 and replay.json() == a, \
        "the original payment retry must return its original body"


def test_snapshot_tokens_stay_frozen_across_a_batch(boot4):
    world = _world(boot4)
    p1, _ = _pay(world, "bob", 100)
    a = p1.json()
    first = assert_status(world.ada.statement(limit=200), 200).json()
    token = first.get("snapshot")
    assert token, f"the first statement must return a snapshot token: {first}"
    frozen = {(e["payment"]["payment_id"], e["delta"]) for e in first["entries"]}

    assert_status(world.op.batch([batch_item(a["payment_id"], 1, 10, a["created_at"])]), 201)
    paged = assert_status(world.ada.statement(snapshot=token, limit=200), 200).json()
    assert {(e["payment"]["payment_id"], e["delta"]) for e in paged["entries"]} == frozen, \
        "a batch must not mutate an existing snapshot"


def test_batch_replay_is_200_identical(boot4):
    world = _world(boot4)
    p1, _ = _pay(world, "bob", 100)
    a = p1.json()
    body = [batch_item(a["payment_id"], 1, 60, a["created_at"])]
    key = new_key()
    first = assert_status(world.op.batch(body, key=key), 201).json()
    replay = world.op.batch(body, key=key)
    assert replay.status_code == 200, f"batch replay must be 200: {replay.text}"
    assert replay.json() == first, "batch replay must return the original response"
    reused = world.op.batch([batch_item(a["payment_id"], 2, 61, a["created_at"])], key=key)
    assert_error(reused, 409, "idempotency_key_reuse")


def test_batch_effective_time_cannot_be_future(boot4):
    world = _world(boot4)
    p1, _ = _pay(world, "bob", 100)
    a = p1.json()
    body = [batch_item(a["payment_id"], 1, 50, plus(3600))]
    assert_error(world.op.batch(body), 422, "validation_failed")
