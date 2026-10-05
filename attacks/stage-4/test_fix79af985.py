"""S4-R10/R12/R14: targeted attacks on the 79af98560dd9 fix round.

The builder's changes touch three places the verifier caught (S4-C10/C12/C14).
These attacks assume the fix is wrong: a partial refund must not disturb the
request link, a no-refund correction must keep the stage-3 decrease, the
refund floor must track cumulative refunds, and duplicate batch ids must lose
to validation, not to a per-item not_found.
"""
from __future__ import annotations

from attacklib4 import (
    assert_error,
    assert_status,
    batch_item,
    new_key,
)

PASSWORD = "correct horse"


def _direct(world, amount=100):
    return assert_status(world.ada.post(
        "/payments", json={"to_handle": "bob", "amount": amount},
        headers={"Idempotency-Key": new_key()}), 201).json()


def _corr(made, amount, rev=1, reason="x"):
    return {"expected_revision": rev, "amount": amount,
            "effective_at": made["created_at"], "reason": reason}


def _paid_request(world, amount=60):
    req = assert_status(world.bob.post(
        "/requests", json={"payer_handle": "ada", "amount": amount},
        headers={"Idempotency-Key": new_key()}), 201).json()
    pay = assert_status(world.ada.post(
        f"/requests/{req['request_id']}/pay", json={},
        headers={"Idempotency-Key": new_key()}), 201).json()
    return req, pay


def test_partial_refund_keeps_paid_request_link(world4):
    req, pay = _paid_request(world4, 60)
    refund = assert_status(world4.bob.refund(pay["payment_id"], 10), 201).json()
    assert refund["refund_of"] == pay["payment_id"]
    listed = assert_status(world4.bob.get("/requests"), 200).json()["requests"]
    row = [r for r in listed if r["request_id"] == req["request_id"]]
    assert row, "the paid request must remain listed after a partial refund"
    assert row[0]["status"] == "paid", f"partial refund changed request status: {row[0]}"
    assert row[0]["payment_id"] == pay["payment_id"], (
        "a partial refund must preserve the request's payment link, "
        f"got {row[0].get('payment_id')} want {pay['payment_id']}")
    # and the target payment still reports its own request link
    activity = assert_status(world4.ada.get("/activity", params={"limit": 200}), 200).json()
    payments = activity.get("payments") if isinstance(activity, dict) else activity
    target = [p for p in payments if p["payment_id"] == pay["payment_id"]]
    assert target and target[0].get("refund_of") is None, "the target is not a refund"


def test_correction_decrease_without_refunds_still_allowed(world4):
    made = _direct(world4, 100)
    assert_status(world4.ada.correct(made["payment_id"], _corr(made, 40)), 201)


def test_correction_floor_uses_cumulative_refunds(world4):
    made = _direct(world4, 100)
    assert_status(world4.bob.refund(made["payment_id"], 30), 201)
    assert_status(world4.bob.refund(made["payment_id"], 30), 201)
    assert_error(world4.ada.correct(made["payment_id"], _corr(made, 59)),
                 422, "refund_exceeds_payment")
    assert_status(world4.ada.correct(made["payment_id"], _corr(made, 60)), 201)
    # exactly refunded out: no headroom for another refund
    assert_error(world4.bob.refund(made["payment_id"], 1), 422, "refund_exceeds_payment")


def test_batch_duplicate_ids_lose_to_not_found(world4):
    unknown = [batch_item("p_missing", 1, 0, "2020-01-01T00:00:00Z"),
               batch_item("p_missing", 1, 0, "2020-01-01T00:00:00Z")]
    assert_error(world4.op.batch(unknown), 422, "validation_failed")
