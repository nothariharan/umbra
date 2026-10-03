"""Stage 2 — stage-1 upgrade compatibility and durability of holds.

S2-R16 (import a stage-1 export keeps the session; pending requests stay payable; a lost
payment stays retryable), S2-R17/R27 (holds survive a snapshot and expiry).
"""
from __future__ import annotations

from attacklib2 import assert_status, fixture2, new_key


def as_stage1_export(export: dict) -> dict:
    """Rewind a stage-2 export to the shape a stage-1 service would have produced."""
    state = dict(export["state"])
    state.pop("authorizations", None)
    state.pop("authorization_ttl_seconds", None)
    return {"track": "pocketful", "format_version": 1, "state": state}


def find_request(client, rid):
    resp = assert_status(client.get("/requests"), 200)
    body = resp.json()
    for item in body["requests"]:
        if item["request_id"] == rid:
            return item
    return None


def test_stage1_export_import_preserves_session_and_pending_request(boot):
    ns = boot(fixture2())
    made = ns.bob.post("/requests", json={"payer_handle": "ada", "amount": 500},
                       headers={"Idempotency-Key": new_key()})
    assert_status(made, 201)
    rid = made.json()["request_id"]

    export = assert_status(ns.ada.get("/_test/export"), 200).json()
    old = as_stage1_export(export)
    assert "authorizations" not in old["state"], "the simulated export is stage-1 shaped"
    assert_status(ns.ada.post("/_test/import", json=old), 204)

    # a browser signed in before the upgrade stays signed in
    assert_status(ns.ada.get("/me"), 200)
    # the existing pending request is still payable
    item = find_request(ns.ada, rid)
    assert item is not None and item["status"] == "pending"
    assert_status(ns.ada.post(f"/requests/{rid}/pay", json={},
                              headers={"Idempotency-Key": new_key()}), 201)


def test_lost_payment_retry_survives_export_import(boot):
    ns = boot(fixture2())
    key = new_key()
    body = {"to_handle": "bob", "amount": 1_000}
    first = ns.ada.post("/payments", json=body, headers={"Idempotency-Key": key})
    assert_status(first, 201)
    pid = first.json()["payment_id"]

    export = assert_status(ns.ada.get("/_test/export"), 200).json()
    assert_status(ns.ada.post("/_test/import", json=as_stage1_export(export)), 204)

    # the original payment and its idempotency record survived: the retry replays
    retry = ns.ada.post("/payments", json=body, headers={"Idempotency-Key": key})
    assert_status(retry, 200)
    assert retry.json()["payment_id"] == pid, "retry must recover the original payment"
    assert ns.ada.me_full()["total"] == 99_000, "money moved exactly once"

    bob_feed = assert_status(ns.bob.get("/activity"), 200).json()
    assert len(bob_feed["payments"]) == 1


def test_hold_survives_export_import_and_is_still_capturable(boot):
    ns = boot(fixture2())
    made = assert_status(ns.ada.authorize("bob", 2_000), 201).json()
    aid = made["authorization_id"]

    export = assert_status(ns.ada.get("/_test/export"), 200).json()
    assert_status(ns.ada.post("/_test/import", json=export), 204)

    ada = ns.ada.me_full()
    assert ada["held"] == 2_000, "a hold must survive a snapshot round trip"
    assert ada["available"] == 98_000
    assert_status(ns.bob.capture(aid, body={}), 201)
    assert ns.ada.me_full()["held"] == 0
    assert ns.ada.me_full()["total"] == 98_000
