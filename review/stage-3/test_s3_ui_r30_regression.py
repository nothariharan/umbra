"""S3-R30: stage 1-2 UI regression on stage-3 build.

Lever `checks --suite uireviewer --stage 3` runs review/stage-2/ against the
stage-3 container; this module marks the stage-3 harness folder without duplicating
Playwright session fixtures.
"""
from __future__ import annotations

import os

import httpx
import pytest

pytestmark = [pytest.mark.stage(3)]


def test_s3_ui_r30_stage3_serves_stage12_html_login():
    base = os.environ.get("BASE_URL", "").rstrip("/")
    assert base, "BASE_URL required"
    resp = httpx.get(
        f"{base}/login",
        headers={"Accept": "text/html"},
        follow_redirects=True,
        timeout=10.0,
    )
    assert resp.status_code < 500
    assert "login-email" in resp.text
