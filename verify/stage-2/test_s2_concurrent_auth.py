"""S2-C27: concurrent authorization/capture correctness (S2-R30)."""
from __future__ import annotations

import pytest

from s2lib.concurrent import burst, no_5xx, tally
from s2lib.http import new_key

pytestmark = pytest.mark.stage(2)


def test_s2_c27_concurrent_authorize_same_key(world, conservation, me_wallet):
    key = new_key()
    body = {"to_handle": "bob", "amount": 40}

    def shoot(_i):
        return world.ada.post("/authorizations", json=body, idempotency_key=key)

    out = burst(shoot, 8)
    no_5xx(out)
    counts = tally(out)
    assert counts.get(201) == 1
    assert counts.get(200) == 7
    conservation(world)
    assert me_wallet(world.ada)["held"] == 40
