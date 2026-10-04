"""S4-C1, S4-C27: delivery extends sealed stage-3 baseline."""
from __future__ import annotations

import pytest

from s4lib import delivery

pytestmark = pytest.mark.stage(4)


def test_s4_c1_prior_stages_and_ten_idempotent_writes():
    assert delivery.extends_sealed_stage3_baseline()[0]
    assert len(delivery.IDEMPOTENT_WRITE_PATHS) == 10


def test_s4_c27_stage4_delivery_artifacts():
    if not delivery.stage_dir_exists():
        pytest.skip("stage-4 not present yet")
    ok, detail = delivery.delivery_files_present()
    assert ok, detail
    ok2, msg2 = delivery.extends_sealed_stage3_baseline()
    assert ok2, msg2
    ok3, msg3 = delivery.run_md_single_command()
    assert ok3, msg3
    ok4, msg4 = delivery.dockerfile_port_contract()
    assert ok4, msg4
