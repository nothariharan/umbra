"""S4-R17, R18, R20, R21: settlement completeness, effective instants, precedence, atomicity."""
from __future__ import annotations

import datetime as _dt

from attacklib4 import (
    assert_error,
    assert_status,
    at_offset,
    batch_item,
    entries_of,
    fixture3,
    new_key,
    parse_ts,
    payment_seed,
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


def _settle(world):
    return assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 100},
            {"from_handle": "ada", "to_handle": "cy", "amount": 100}]},
        headers={"Idempotency-Key": new_key()}), 201).json()


def _item(made, amount=0, *, effective_at=None, rev=1):
    return batch_item(made["payment_id"], rev, amount, effective_at or made["created_at"])


def test_correcting_one_settlement_member_is_incomplete(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    members = _settle(world)["payments"]
    assert_error(world.op.batch([_item(members[0], 50)]), 422, "incomplete_settlement")


def test_settlement_members_must_share_effective_instant(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    members = _settle(world)["payments"]
    t = members[0]["created_at"]
    mismatch = [_item(members[0], 50, effective_at=t),
                _item(members[1], 50, effective_at=at_offset(
                    parse_ts(t) + _dt.timedelta(seconds=5), 0))]
    assert_error(world.op.batch(mismatch), 422, "validation_failed")
    # identical instant written with a different offset is accepted
    same = [_item(members[0], 50, effective_at=t),
            _item(members[1], 50, effective_at=at_offset(parse_ts(t), 3))]
    assert_status(world.op.batch(same), 201)


def test_precedence_item_error_before_completeness(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    members = _settle(world)["payments"]
    body = [_item(members[0], 50),
            batch_item("p_missing", 1, 0, members[0]["created_at"])]
    assert_error(world.op.batch(body), 404, "not_found")


def test_precedence_completeness_before_funds(boot4):
    # a valid settlement exists; a batch that omits a member and is wildly unaffordable must
    # report the settlement-completeness error, not insufficient_funds.
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    members = _settle(world)["payments"]
    body = [_item(members[0], 10_000_000)]
    assert_error(world.op.batch(body), 422, "incomplete_settlement")


def test_rejected_batch_is_atomic_and_frees_its_key(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    made = assert_status(world.ada.post(
        "/payments", json={"to_handle": "bob", "amount": 100},
        headers={"Idempotency-Key": new_key()}), 201).json()
    before_total = sum(c.me_full()["balance"] for c in world.all)
    before_entries = len(entries_of(world.ada.statement(limit=200)))
    key = new_key()
    bad = world.op.batch([_item(made, 50, rev=9)], key=key)
    assert_error(bad, 409, "stale_revision")
    assert sum(c.me_full()["balance"] for c in world.all) == before_total, \
        "a rejected batch must not move money"
    assert len(entries_of(world.ada.statement(limit=200))) == before_entries
    # after a 4xx the key is reusable as a first use
    good = world.op.batch([_item(made, 120)], key=key)
    assert good.status_code == 201, f"key after a failed batch must be reusable: {good.text}"


def test_historical_overdraft_precedence_over_current(boot4):
    world = boot4(fixture3(users=_users(ada=1000, bob=0, cy=0, op=0), operators=["u_op"],
                           payments=[
                               payment_seed("p1", "u_ada", "u_bob", 900,
                                            created_at="2026-09-24T06:00:00+00:00"),
                               payment_seed("p2", "u_bob", "u_ada", 900,
                                            created_at="2026-09-24T07:00:00+00:00")] ))
    item = batch_item("p1", 1, 1500, "2026-09-24T06:00:00+00:00")
    assert_error(world.op.batch([item]), 409, "historical_overdraft")
    assert world.ada.me_full()["balance"] == 1000, "state must be preserved"
