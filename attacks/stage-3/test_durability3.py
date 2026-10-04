"""S3-R24, R29: export/import round trips carry the stage-3 ledger and links."""
from __future__ import annotations

from attacklib3 import (
    Client,
    assert_error,
    assert_status,
    authz,
    correction_body,
    entries_of,
    fixture3,
    future_iso,
    new_key,
)

PASSWORD = "correct horse"


def _users(ada=1000, bob=0, op=1000):
    return [
        {"id": "u_ada", "email": "ada@example.com", "password": PASSWORD,
         "display_name": "Ada", "handle": "ada", "balance": ada},
        {"id": "u_bob", "email": "bob@example.com", "password": PASSWORD,
         "display_name": "Bob", "handle": "bob", "balance": bob},
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


def test_round_trip_preserves_balances_tokens_and_statement(boot3, reset):
    world = boot3(fixture3(users=_users(), operators=[]))
    made = assert_status(world.ada.post(
        "/payments", json={"to_handle": "bob", "amount": 123},
        headers={"Idempotency-Key": new_key()}), 201).json()
    ada_after = world.ada.balance()
    bob_after = world.bob.balance()

    exported = assert_status(_export(), 200).json()
    reset(fixture3(users=_users(5, 5), operators=[]))  # a different state
    assert_status(_import(exported), 204)

    assert world.ada.balance() == ada_after, "import must restore balances"
    assert world.bob.balance() == bob_after
    entries = entries_of(world.ada.statement(limit=200))
    assert made["payment_id"] in {e["payment"]["payment_id"] for e in entries}, \
        "imported payments must appear in the statement"


def test_authorization_ledger_survives_import_and_capture_stays_immutable(boot3, reset):
    world = boot3(fixture3(users=_users(), operators=[], authorizations=[
        authz("a_seed", "u_ada", "u_bob", 300, expires_at=future_iso(7200)),
    ]))
    exported = assert_status(_export(), 200).json()
    reset(fixture3(users=_users(7, 7), operators=[]))
    assert_status(_import(exported), 204)

    listing = assert_status(world.ada.list_authorizations(limit=50), 200).json()
    items = listing.get("authorizations") if isinstance(listing, dict) else listing
    assert any((a.get("authorization_id") or a.get("id")) == "a_seed" for a in items), \
        "the authorization ledger must survive import"

    captured = assert_status(world.bob.capture("a_seed", amount=300), 201).json()
    resp = world.ada.correct(captured["payment_id"],
                             correction_body(1, 100, captured["created_at"], "x"))
    assert_error(resp, 422, "linked_payment_immutable")


def test_settlement_member_stays_immutable_after_import(boot3, reset):
    world = boot3(fixture3(users=_users(), operators=["u_op"]))
    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 100}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    exported = assert_status(_export(), 200).json()
    reset(fixture3(users=_users(3, 3), operators=["u_op"]))
    assert_status(_import(exported), 204)
    member = settled["payments"][0]
    resp = world.ada.correct(member["payment_id"],
                             correction_body(1, 50, member["created_at"], "x"))
    assert_error(resp, 422, "linked_payment_immutable")
