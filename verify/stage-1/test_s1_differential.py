"""S1-C31: differential replay against reference_model oracle."""
from __future__ import annotations

import random

import pytest

from lib import fixtures as fx
from lib.http import new_key
from lib.reference_model import ModelError, model_from_fixture

pytestmark = pytest.mark.stage(1)


def test_s1_c31_differential_payments_match_reference(world, conservation):
    model = model_from_fixture(world.fixture)
    clients = [world.ada, world.bob, world.cy]
    rng = random.Random(0xC31)

    for step in range(150):
        actor = rng.choice(clients)
        me = actor.get("/me").json()
        actor_id = me["user_id"]
        targets = [h for h in ("ada", "bob", "cy") if h != me["handle"]]
        to_handle = rng.choice(targets)
        amount = rng.randint(1, 60)
        resp = actor.post(
            "/payments",
            json={"to_handle": to_handle, "amount": amount},
            idempotency_key=new_key(),
        )
        assert resp.status_code in (201, 409), resp.text
        assert resp.status_code < 500
        if resp.status_code == 201:
            model.pay_handle(actor_id, to_handle, amount)
        else:
            with pytest.raises(ModelError):
                model.pay_handle(actor_id, to_handle, amount)

        for client in clients:
            uid = client.get("/me").json()["user_id"]
            assert client.get("/me").json()["balance"] == model.balance(uid)
        assert model.conservation_ok()
        conservation(world)
