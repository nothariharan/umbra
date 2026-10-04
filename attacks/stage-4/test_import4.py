"""S4-R26: a stage-4 service accepts stages 1-3 exports and keeps their ledger intact."""
from __future__ import annotations

from attacklib4 import (
    Client,
    assert_status,
    entries_of,
    fixture3,
    new_key,
    revisions_of,
)

PASSWORD = "correct horse"


def _users(ada=1000, bob=1000, cy=1000, op=1000):
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


def _export():
    c = Client()
    try:
        return c.get("/_test/export", token=None)
    finally:
        c.close()


def _import(obj):
    c = Client()
    try:
        return c.post("/_test/import", json=obj, token=None)
    finally:
        c.close()


def _seed_ledger(world):
    made = assert_status(world.ada.post(
        "/payments", json={"to_handle": "bob", "amount": 200},
        headers={"Idempotency-Key": new_key()}), 201).json()
    assert_status(world.ada.correct(made["payment_id"], {
        "expected_revision": 1, "amount": 150, "effective_at": made["created_at"],
        "reason": "trim"}), 201)
    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 40}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    return made, settled["payments"][0]


def test_export_import_round_trip_is_unchanged(boot4):
    from attacklib4 import do_reset
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    _seed_ledger(world)
    exported = assert_status(_export(), 200).json()
    do_reset(fixture3(users=_users(5, 5, 5, 5), operators=["u_op"]))
    assert_status(_import(exported), 204)
    again = assert_status(_export(), 200).json()
    assert again == exported, "re-exporting an imported snapshot must be unchanged"


def test_import_preserves_corrections_membership_and_snapshot(boot4):
    world = boot4(fixture3(users=_users(), operators=["u_op"]))
    made, member = _seed_ledger(world)
    snapshot = assert_status(world.ada.statement(limit=200), 200).json()
    token = snapshot.get("snapshot")
    assert token, "the statement must return a snapshot token"

    exported = assert_status(_export(), 200).json()
    from attacklib4 import do_reset
    do_reset(fixture3(users=_users(9, 9, 9, 9), operators=["u_op"]))
    assert_status(_import(exported), 204)

    revs = revisions_of(world.ada.revisions(made["payment_id"]))
    assert len(revs) == 2 and revs[-1]["amount"] == 150, \
        f"import must retain corrections: {revs}"
    entries = {e["payment"]["payment_id"]: e for e in
               entries_of(world.ada.statement(limit=200))}
    assert entries[made["payment_id"]]["payment"]["amount"] == 150
    # settlement membership survived
    account = assert_status(world.bob.get("/activity", params={"limit": 200}), 200).json()
    rows = account.get("payments") if isinstance(account, dict) else account
    live = [p for p in rows if p["payment_id"] == member["payment_id"]]
    assert live and live[0].get("settlement_id"), "import must retain settlement membership"
    # the pre-import snapshot token still pages its frozen entries
    paged = world.ada.statement(snapshot=token, limit=200)
    assert paged.status_code == 200, f"import must retain snapshots: {paged.status_code}"
