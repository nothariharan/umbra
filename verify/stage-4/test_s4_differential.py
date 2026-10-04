"""Differential replay: refunds + corrections with conservation (S4-R1 invariants)."""
from __future__ import annotations

import random

import pytest

from s3lib.http import new_key

pytestmark = pytest.mark.stage(4)

EFFECTIVE = "2026-09-20T12:00:00+00:00"


def test_s4_differential_refunds_and_corrections(world, conservation, pay, refund, reset):
    rng = random.Random(0x534)
    pid = None
    for _ in range(30):
        op = rng.choice(("pay", "refund", "correct"))
        if op == "pay" or pid is None:
            amount = rng.randint(10, 80)
            resp = pay(amount=amount, to_handle=rng.choice(["bob", "cy"]))
            if resp.status_code == 201:
                pid = resp.json()["payment_id"]
            conservation(world)
            continue
        if op == "refund" and pid:
            amount = rng.randint(1, 40)
            refund(world.bob if rng.random() < 0.5 else world.bob, pid, amount)
            conservation(world)
            continue
        if pid:
            body = {
                "expected_revision": 1,
                "amount": rng.randint(0, 100),
                "effective_at": EFFECTIVE,
                "reason": "diff",
            }
            world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=new_key())
            conservation(world)
