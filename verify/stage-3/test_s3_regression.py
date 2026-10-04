"""S3-C30: stage 1–2 UI testids/flows on stage-3 build; S3-C1 runtime regression hook."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.stage(3)


def test_s3_c30_stage12_ui_checks_on_stage3_build():
    base = os.environ.get("BASE_URL")
    if not base:
        pytest.skip("BASE_URL required for UI regression on running stage-3 service")
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    py = sys.executable
    stage2 = os.path.join(repo, "verify", "stage-2")
    nodes = [
        "test_s2_ui_testids.py::test_s2_c4_home_wallet_and_pay_testids",
        "test_s2_ui_flows.py::test_s2_c11_balance_feed_refresh_after_pay",
    ]
    env = {**os.environ, "BASE_URL": base}
    proc = subprocess.run(
        [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", *nodes],
        cwd=stage2,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
