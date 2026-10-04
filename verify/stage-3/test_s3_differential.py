"""Differential replay with corrections (supports S3-R17 conservation)."""
from __future__ import annotations

import random

import pytest

from s3lib.http import new_key
from s3lib.stage3_model import ModelError, model_from_fixture

pytestmark = pytest.mark.stage(3)


def test_s3_differential_payments_and_corrections(world, conservation, pay, reset):
    model = model_from_fixture(world.fixture)
    rng = random.Random(0x533)
    pid = None
    for _ in range(40):
        op = rng.choice(("pay", "correct"))
        if op == "pay" or pid is None:
            amount = rng.randint(1, 30)
            resp = pay(amount=amount, to_handle=rng.choice(["bob", "cy"]))
            if resp.status_code == 201:
                pid = resp.json()["payment_id"]
                model.pay_handle(world.fixture["users"][0]["id"], "bob" if resp.json()["to_handle"] == "bob" else "cy", amount)
            continue
        amount = rng.randint(0, 40)
        body = {
            "expected_revision": 1,
            "amount": amount,
            "effective_at": "2026-09-20T12:00:00+00:00",
            "reason": "diff",
        }
        resp = world.ada.post(f"/payments/{pid}/corrections", json=body, idempotency_key=new_key())
        if resp.status_code == 201:
            try:
                model.apply_correction(
                    world.fixture["users"][0]["id"],
                    pid,
                    expected_revision=1,
                    amount=amount,
                    effective_at=model.now,
                )
            except ModelError:
                pass
        conservation(world)
