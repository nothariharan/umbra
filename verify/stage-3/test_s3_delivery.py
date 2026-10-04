"""S3-C1, S3-C29: delivery extends sealed stage-2 baseline."""
from __future__ import annotations

import pytest

from s3lib import delivery

pytestmark = pytest.mark.stage(3)


def test_s3_c1_prior_stages_continue():
    assert delivery.extends_stage2_baseline()[0]


def test_s3_c29_stage3_delivery_artifacts():
    if not delivery.stage_dir_exists():
        pytest.skip("stage-3 not present yet")
    ok, detail = delivery.delivery_files_present()
    assert ok, detail
    ok2, msg2 = delivery.extends_stage2_baseline()
    assert ok2, msg2
    ok3, msg3 = delivery.run_md_single_command()
    assert ok3, msg3
    ok4, msg4 = delivery.dockerfile_port_contract()
    assert ok4, msg4
