"""S4-C28: stage 1–3 UI checks on stage-4 build; runtime stage-3 regression hook."""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.stage(4)


def test_s4_c28_stage123_ui_on_stage4_build():
    base = os.environ.get("BASE_URL")
    if not base:
        pytest.skip("BASE_URL required for UI regression on running stage-4 service")
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


def test_s4_runtime_stage3_smoke_on_stage4_service():
    base = os.environ.get("BASE_URL")
    if not base:
        pytest.skip("BASE_URL required")
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    py = sys.executable
    stage3 = os.path.join(repo, "verify", "stage-3")
    node = "test_s3_timestamps.py::test_s3_c2_created_at_on_payment_endpoints"
    env = {**os.environ, "BASE_URL": base}
    proc = subprocess.run(
        [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", node],
        cwd=stage3,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
