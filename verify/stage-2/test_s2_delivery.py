"""S2-C1: stage-2 delivery extends stage-1 (S2-R31)."""
from __future__ import annotations

import pytest

from lib import delivery

pytestmark = pytest.mark.stage(2)


def test_s2_c1_stage2_delivery_artifacts():
    if not delivery.stage_dir_exists():
        pytest.skip("stage-2 not present yet; run after Builder SUBMIT")
    ok, detail = delivery.delivery_files_present()
    assert ok, detail
    ok1, msg1 = delivery.extends_stage1_baseline()
    assert ok1, msg1


def test_s2_c1_run_md_and_docker():
    if not delivery.stage_dir_exists():
        pytest.skip("stage-2 not present yet")
    ok, detail = delivery.run_md_single_command()
    assert ok, detail
    ok_d, msg_d = delivery.dockerfile_port_contract()
    assert ok_d, msg_d
