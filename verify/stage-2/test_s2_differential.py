"""S2-C28: differential replay with authorizations (S2-R30, S2-R17)."""
from __future__ import annotations

import random

import pytest

from lib.http import new_key
from lib.reference_model import ModelError, model_from_fixture

pytestmark = pytest.mark.stage(2)


def test_s2_c28_differential_payments_and_holds(world, conservation, me_wallet):
    model = model_from_fixture(world.fixture)
    clients = [world.ada, world.bob, world.cy]
    rng = random.Random(0xC28)

    for _ in range(120):
        actor = rng.choice(clients)
        me = me_wallet(actor)
        actor_id = me["user_id"]
        op = rng.choice(("pay", "auth"))
        to_handle = rng.choice([h for h in ("ada", "bob", "cy") if h != me["handle"]])
        amount = rng.randint(1, 40)
        if op == "pay":
            resp = actor.post(
                "/payments",
                json={"to_handle": to_handle, "amount": amount},
                idempotency_key=new_key(),
            )
            assert resp.status_code in (201, 409)
            if resp.status_code == 201:
                model.pay_handle(actor_id, to_handle, amount)
            else:
                with pytest.raises(ModelError):
                    model.pay_handle(actor_id, to_handle, amount)
        else:
            resp = actor.post(
                "/authorizations",
                json={"to_handle": to_handle, "amount": amount},
                idempotency_key=new_key(),
            )
            assert resp.status_code in (201, 409)
            if resp.status_code == 201:
                model.create_authorization(actor_id, to_handle, amount)
            else:
                with pytest.raises(ModelError):
                    model.create_authorization(actor_id, to_handle, amount)

        for client in clients:
            uid = me_wallet(client)["user_id"]
            assert me_wallet(client)["balance"] == model.balance(uid)
        conservation(world)
