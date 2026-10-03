"""Settlement attacks: atomic net batches, collective affordability, permissions.

Class: concurrency / balance. A batch is affordable on post-batch balances, not on
the order the transfers happen to be listed in.
"""
from __future__ import annotations

from attacklib import Client, assert_error, assert_status, fixture, new_key, user

SETTLE = "/settlements"
PAY = "/payments"


def _settle(client, transfers, *, key=None):
    return client.post(SETTLE, json={"transfers": transfers},
                       headers={"Idempotency-Key": key or new_key()})


def _op_world(boot, users, *, handles=("ada", "bob", "op"), operators=("u_op",)):
    return boot(fixture(users=users, operators=list(operators)), handles=handles)


def test_no_token_is_401(boot):
    w = _op_world(boot, [user("ada", 100), user("bob", 0), user("op", 100, uid="u_op")])
    anon = w.api()
    r = anon.post(SETTLE, json={"transfers": [
        {"from_handle": "op", "to_handle": "bob", "amount": 10}]},
        headers={"Idempotency-Key": new_key()})
    assert_error(r, 401, "unauthenticated")


def test_non_operator_is_403(boot):
    w = _op_world(boot, [user("ada", 100), user("bob", 0), user("op", 100, uid="u_op")])
    r = _settle(w.ada, [{"from_handle": "ada", "to_handle": "bob", "amount": 10}])
    assert_error(r, 403, "forbidden")


def test_collective_net_zero_batch_commits_even_with_zero_wallets(boot):
    """ada=0 and bob=0, but ada->bob 100 and bob->ada 100 nets to zero: it is affordable."""
    w = _op_world(boot, [user("ada", 0), user("bob", 0), user("op", 0, uid="u_op")])
    r = _settle(w.op, [{"from_handle": "ada", "to_handle": "bob", "amount": 100},
                       {"from_handle": "bob", "to_handle": "ada", "amount": 100}])
    assert_status(r, 201)
    assert w.ada.balance() == 0
    assert w.bob.balance() == 0
    assert len(r.json()["payments"]) == 2


def test_collective_insufficient_funds_is_409_and_atomic(boot):
    w = _op_world(boot, [user("ada", 0), user("bob", 0), user("op", 0, uid="u_op")])
    before = len(w.ada.get("/activity").json()["payments"])
    r = _settle(w.op, [{"from_handle": "ada", "to_handle": "bob", "amount": 100}])
    assert_error(r, 409, "insufficient_funds")
    assert w.ada.balance() == 0 and w.bob.balance() == 0
    assert len(w.ada.get("/activity").json()["payments"]) == before, "partial batch committed"


def test_entry_error_beats_insufficient_funds(boot):
    w = _op_world(boot, [user("ada", 0), user("bob", 0), user("op", 0, uid="u_op")])
    r = _settle(w.op, [{"from_handle": "ada", "to_handle": "bob", "amount": 100},
                       {"from_handle": "ghost", "to_handle": "bob", "amount": 1}])
    assert_error(r, 404, "not_found")
    assert w.ada.balance() == 0


def test_self_transfer_is_422(boot):
    w = _op_world(boot, [user("ada", 100), user("bob", 0), user("op", 0, uid="u_op")])
    r = _settle(w.op, [{"from_handle": "ada", "to_handle": "ada", "amount": 1}])
    assert_error(r, 422, "self_payment")


def test_batch_size_boundaries(boot):
    users = [user("op", 10_000, uid="u_op")] + [user(f"r{i}", 0) for i in range(33)]
    handles = ("op",) + tuple(f"r{i}" for i in range(33))
    w = _op_world(boot, users, handles=handles)
    one = _settle(w.op, [{"from_handle": "op", "to_handle": "r0", "amount": 1}])
    assert_status(one, 201)

    over = _settle(w.op, [{"from_handle": "op", "to_handle": f"r{i}", "amount": 1}
                          for i in range(33)])
    assert_error(over, 422, "validation_failed")

    empty = _settle(w.op, [])
    assert_error(empty, 422, "validation_failed")


def test_malformed_batch_shapes_are_422(boot):
    w = _op_world(boot, [user("ada", 100), user("bob", 0), user("op", 0, uid="u_op")])
    for transfers in (
        {"from_handle": "ada", "to_handle": "bob", "amount": 1},
        [{"to_handle": "bob", "amount": 1}],
        [{"from_handle": "ada", "to_handle": "bob", "amount": 0}],
        [{"from_handle": "ada", "to_handle": "bob", "amount": "1"}],
    ):
        r = w.op.post(SETTLE, json={"transfers": transfers},
                      headers={"Idempotency-Key": new_key()})
        assert_error(r, 422, "validation_failed")


def test_success_shape_and_order(boot):
    w = _op_world(boot, [user("ada", 0), user("bob", 0), user("cy", 0),
                         user("op", 1000, uid="u_op")],
                  handles=("ada", "bob", "cy", "op"))
    transfers = [{"from_handle": "op", "to_handle": "bob", "amount": 300},
                 {"from_handle": "op", "to_handle": "cy", "amount": 200},
                 {"from_handle": "op", "to_handle": "ada", "amount": 100}]
    r = _settle(w.op, transfers)
    assert_status(r, 201)
    body = r.json()
    assert body.get("settlement_id")
    assert body.get("committed_at")
    payments = body["payments"]
    assert [p["to_handle"] for p in payments] == ["bob", "cy", "ada"]
    assert [p["amount"] for p in payments] == [300, 200, 100]
    for p in payments:
        assert p["settlement_id"] == body["settlement_id"]
        assert p["request_id"] is None
        assert p["created_at"] == body["committed_at"]
    assert w.op.balance() == 1000 - 600
    assert w.bob.balance() == 300 and w.cy.balance() == 200 and w.ada.balance() == 100


def test_direct_payment_is_a_nonmember(world):
    r = world.ada.post(PAY, json={"to_handle": "bob", "amount": 10},
                       headers={"Idempotency-Key": new_key()})
    assert_status(r, 201)
    assert r.json().get("settlement_id") is None, \
        "a payment outside a settlement must expose null settlement_id"


def test_export_import_preserves_operator_permission(boot):
    w = _op_world(boot, [user("ada", 0), user("bob", 0), user("op", 1000, uid="u_op")])
    snap = Client()
    try:
        exported = snap.get("/_test/export")
        assert_status(exported, 200)
    finally:
        snap.close()
    importer = Client()
    try:
        assert_status(importer.post("/_test/import", json=exported.json()), 204)
    finally:
        importer.close()
    r = _settle(w.op, [{"from_handle": "op", "to_handle": "bob", "amount": 100}])
    assert_status(r, 201,)


def test_operator_permission_does_not_leak_private_data(boot):
    w = _op_world(boot, [user("ada", 1000), user("bob", 0), user("op", 0, uid="u_op")])
    paid = w.ada.post(PAY, json={"to_handle": "bob", "amount": 100,
                                 "visibility": "private"},
                      headers={"Idempotency-Key": new_key()})
    assert_status(paid, 201)
    pid = paid.json()["payment_id"]
    assert all(p["payment_id"] != pid
               for p in w.op.get("/activity").json()["payments"]), \
        "operator saw another user's private payment"

    made = w.bob.post("/requests", json={"payer_handle": "ada", "amount": 50},
                      headers={"Idempotency-Key": new_key()})
    assert_status(made, 201)
    rid = made.json()["request_id"]
    assert all(q["request_id"] != rid
               for q in w.op.get("/requests").json()["requests"]), \
        "operator saw another user's request"
