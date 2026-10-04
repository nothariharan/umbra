"""S4-R24..S4-R26: settlement refunds, concurrency, import."""
from __future__ import annotations

import concurrent.futures

import httpx
import pytest

from s3lib import fixtures as fx
from s3lib.http import assert_status, new_key

pytestmark = pytest.mark.stage(4)

EFFECTIVE = "2026-09-20T12:00:00+00:00"


def test_s4_c24_settlement_member_refund_keeps_membership(reset, world, refund):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "settle_p",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 300,
                "visibility": "private",
                "settlement_id": "s1",
                "created_at": EFFECTIVE,
            }
        ]
    )
    reset(fx_body)
    assert_status(refund(world.bob, "settle_p", 100), 201)
    acts = assert_status(world.ada.get("/activity"), 200).json()["payments"]
    settle = next(p for p in acts if p["payment_id"] == "settle_p")
    assert settle.get("settlement_id") == "s1"


def test_s4_c25_concurrent_corrections_same_revision(reset, world):
    pid = "pay1"
    reset(
        fx.fixture(
            payments=[
                {
                    "id": pid,
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 500,
                    "visibility": "public",
                    "created_at": EFFECTIVE,
                }
            ]
        )
    )
    body = {
        "expected_revision": 1,
        "amount": 480,
        "effective_at": EFFECTIVE,
        "reason": "race",
    }

    def attempt():
        return world.ada.post(
            f"/payments/{pid}/corrections",
            json=body,
            idempotency_key=new_key(),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        r1, r2 = [f.result() for f in (pool.submit(attempt), pool.submit(attempt))]
    assert sum(r.status_code == 201 for r in (r1, r2)) <= 1


def test_s4_c26_import_stage3_export_retains_state(reset, world, api, base_url):
    pid = "pay1"
    reset(
        fx.fixture(
            payments=[
                {
                    "id": pid,
                    "from_user_id": fx.ADA["id"],
                    "to_user_id": fx.BOB["id"],
                    "amount": 400,
                    "visibility": "public",
                    "created_at": EFFECTIVE,
                }
            ]
        )
    )
    assert_status(
        world.ada.post(
            f"/payments/{pid}/corrections",
            json={
                "expected_revision": 1,
                "amount": 350,
                "effective_at": EFFECTIVE,
                "reason": "pre-export",
            },
            idempotency_key=new_key(),
        ),
        201,
    )
    snap = assert_status(world.ada.get("/statement"), 200).json()
    export = assert_status(httpx.get(f"{base_url}/_test/export"), 200).json()
    reset(fx.fixture())
    assert_status(httpx.post(f"{base_url}/_test/import", json=export, timeout=10.0), 204)
    stmt2 = assert_status(world.ada.get("/statement"), 200).json()
    assert stmt2["closing_balance"] == snap["closing_balance"]
