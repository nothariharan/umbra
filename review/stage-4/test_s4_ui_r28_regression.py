"""S4-R28: stage 1-3 UI regression on stage-4 build.

Lever `checks --suite uireviewer --stage 4` runs review/stage-2/ and review/stage-3/
against the stage-4 container; this module marks the stage-4 harness folder.
"""
from __future__ import annotations

import os

import httpx
import pytest

pytestmark = [pytest.mark.stage(4)]


def test_s4_ui_r28_stage4_serves_stage12_html_login():
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
