"""S4-R2..R10, R24: refund authorization, targets, amounts, funds and links."""
from __future__ import annotations

from attacklib4 import (
    assert_error,
    assert_status,
    authz,
    fixture3,
    future_iso,
    new_key,
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


def _pay(client, to_handle, amount, *, note=None, visibility=None):
    body = {"to_handle": to_handle, "amount": amount}
    if note is not None:
        body["note"] = note
    if visibility is not None:
        body["visibility"] = visibility
    return client.post("/payments", json=body, headers={"Idempotency-Key": new_key()})


def _direct(world, amount=100, *, note=None, visibility=None):
    return assert_status(_pay(world.ada, "bob", amount, note=note, visibility=visibility),
                         201).json()


def test_refund_requires_key_receiver_and_known_payment(world4):
    made = _direct(world4, 100)
    pid = made["payment_id"]
    # missing/empty key -> 400
    assert_error(world4.bob.refund(pid, 100, key_sent=False), 400, "missing_idempotency_key")
    # sender and third party are not the original receiver
    assert_error(world4.ada.refund(pid, 100), 403, "forbidden")
    assert_error(world4.cy.refund(pid, 100), 403, "forbidden")
    # unknown payment -> 404 (checked as the receiver role)
    assert_error(world4.bob.refund("p_missing", 100), 404, "not_found")


def test_refund_amount_validation_table(world4):
    made = _direct(world4, 100)
    pid = made["payment_id"]
    for body in [{}, {"amount": None}, {"amount": 0}, {"amount": -1}, {"amount": 1.5},
                 {"amount": "100"}, {"amount": True}, {"amount": [100]}]:
        resp = world4.bob.refund(pid, body=body)
        assert resp.status_code == 422, f"refund body {body!r} must be 422, got {resp.status_code}"
        assert resp.json().get("error", {}).get("code") == "validation_failed", resp.text


def test_refund_target_kinds_and_refund_of_refund(world4):
    direct = _direct(world4, 100)
    first = assert_status(world4.bob.refund(direct["payment_id"], 40), 201).json()
    # the refund itself is from bob -> ada, so ada is now the receiver, but a refund is
    # never a valid target for anyone.
    assert_error(world4.ada.refund(first["payment_id"], 10), 422, "invalid_refund_target")
    assert_error(world4.bob.refund(first["payment_id"], 10), 422, "invalid_refund_target")

    # request payment: bob requests from ada, ada pays -> ada sender, bob receiver
    req = assert_status(world4.bob.post(
        "/requests", json={"payer_handle": "ada", "amount": 60},
        headers={"Idempotency-Key": new_key()}), 201).json()
    req_pay = assert_status(world4.ada.post(
        f"/requests/{req['request_id']}/pay", json={}, headers={"Idempotency-Key": new_key()}),
        201).json()
    assert_status(world4.bob.refund(req_pay["payment_id"], 60), 201)

    # capture payment: ada authorizes bob, bob captures
    authorized = assert_status(world4.ada.authorize(
        "bob", 80, note="cap", visibility="private"), 201).json()
    cap = assert_status(world4.bob.capture(authorized["authorization_id"], amount=80), 201).json()
    assert_status(world4.bob.refund(cap["payment_id"], 80), 201)


def test_refund_shape_and_idempotent_replay(world4):
    made = _direct(world4, 100, note="lunch", visibility="public")
    pid = made["payment_id"]
    key = new_key()
    first = assert_status(world4.bob.refund(pid, 40, key=key), 201).json()

    assert first["refund_of"] == pid, f"refund_of must name the target: {first}"
    assert first["request_id"] is None, "refunds carry request_id null"
    assert first["authorization_id"] is None, "refunds carry authorization_id null"
    assert first["from_user_id"] == made["to_user_id"], "refund reverses direction"
    assert first["to_user_id"] == made["from_user_id"]
    assert first["amount"] == 40
    assert first["note"] == "lunch" and first["visibility"] == "public", \
        "a refund keeps the original note and visibility"

    replay = world4.bob.refund(pid, 40, key=key)
    assert replay.status_code == 200, f"replay must be 200. {replay.status_code}"
    assert replay.json() == first, "replay must return the original body"
    reused = world4.bob.refund(pid, 41, key=key)
    assert_error(reused, 409, "idempotency_key_reuse")

    # a non-refund payment keeps refund_of null
    entries = assert_status(world4.ada.get("/activity", params={"limit": 200}), 200).json()
    payments = entries.get("payments") if isinstance(entries, dict) else entries
    target = [p for p in payments if p["payment_id"] == pid]
    assert target and target[0].get("refund_of") is None, "original payment has refund_of null"


def test_cumulative_refunds_cannot_exceed_corrected_amount(world4):
    made = _direct(world4, 100)
    pid = made["payment_id"]
    assert_status(world4.bob.refund(pid, 60), 201)
    assert_status(world4.bob.refund(pid, 40), 201)
    assert_error(world4.bob.refund(pid, 1), 422, "refund_exceeds_payment")
    # a single oversized refund is rejected before any money moves
    other = _direct(world4, 100)
    bob_before = world4.bob.balance()
    assert_error(world4.bob.refund(other["payment_id"], 150), 422, "refund_exceeds_payment")
    assert world4.bob.balance() == bob_before


def test_refund_debits_receiver_available_and_fails_409(boot4):
    world = boot4(fixture3(users=_users(ada=1000, bob=50, cy=0, op=0), operators=[]))
    made = _direct(world, 100)
    bob_before = world.bob.balance()
    assert_error(world.bob.refund(made["payment_id"], 60), 409, "insufficient_funds")
    assert world.bob.balance() == bob_before, "a failed refund must not move money"
    ok = assert_status(world.bob.refund(made["payment_id"], 50), 201).json()
    assert world.bob.balance() == bob_before - 50
    assert world.ada.balance() == 1000 - 100 + 50


def test_refund_never_reopens_request_or_authorization(world4):
    # request stays paid
    req = assert_status(world4.bob.post(
        "/requests", json={"payer_handle": "ada", "amount": 60},
        headers={"Idempotency-Key": new_key()}), 201).json()
    req_pay = assert_status(world4.ada.post(
        f"/requests/{req['request_id']}/pay", json={}, headers={"Idempotency-Key": new_key()}),
        201).json()
    assert_status(world4.bob.refund(req_pay["payment_id"], 60), 201)
    listed = assert_status(world4.bob.get("/requests"), 200).json()["requests"]
    row = [r for r in listed if r["request_id"] == req["request_id"]]
    assert row and row[0]["status"] == "paid" and row[0]["payment_id"] == req_pay["payment_id"], \
        "a refund must not reopen the request"

    # authorization stays captured and the hold is not restored
    authorized = assert_status(world4.ada.authorize("bob", 80), 201).json()
    cap = assert_status(world4.bob.capture(authorized["authorization_id"], amount=80), 201).json()
    assert_status(world4.bob.refund(cap["payment_id"], 80), 201)
    auth = world4.ada.find_authorization(authorized["authorization_id"])
    assert auth is not None and auth.get("status") == "captured", \
        f"a refund must not reopen the authorization: {auth}"
    assert world4.ada.wallet()[3] == 0, "a refund must not restore a released hold"


def test_refund_of_settlement_member_keeps_membership(boot4):
    world = boot4(fixture3(users=_users(ada=1000, bob=1000, cy=1000, op=1000),
                           operators=["u_op"]))
    settled = assert_status(world.op.post(
        "/settlements", json={"transfers": [
            {"from_handle": "ada", "to_handle": "bob", "amount": 100},
            {"from_handle": "ada", "to_handle": "cy", "amount": 100}]},
        headers={"Idempotency-Key": new_key()}), 201).json()
    member = settled["payments"][0]
    sid = member.get("settlement_id")
    assert sid, f"a settlement member must expose settlement_id: {member}"
    refunded = assert_status(world.bob.refund(member["payment_id"], 100), 201).json()
    members = assert_status(world.bob.get("/activity", params={"limit": 200}), 200).json()
    rows = members.get("payments") if isinstance(members, dict) else members
    still = [p for p in rows if p["payment_id"] == member["payment_id"]]
    assert still and still[0].get("settlement_id") == sid, \
        "a refund must not change settlement membership"
    assert refunded.get("settlement_id") in (None, ""), "a refund is not a settlement member"


def test_refund_cap_tracks_corrected_amount(world4):
    made = _direct(world4, 100)
    pid = made["payment_id"]
    assert_status(world4.ada.correct(pid, {
        "expected_revision": 1, "amount": 150, "effective_at": made["created_at"],
        "reason": "raise"}), 201)
    assert_status(world4.bob.refund(pid, 120), 201)
    assert_error(world4.bob.refund(pid, 40), 422, "refund_exceeds_payment")
