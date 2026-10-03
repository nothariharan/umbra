"""Pytest fixtures for Pocketful Stage 2 UI review (Playwright)."""
from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = os.path.dirname(__file__)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib.ui import VIEWPORTS, require_html_ui  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line("markers", "stage(n): stage number for regress filtering")


@pytest.fixture(scope="session")
def base_url() -> str:
    url = os.environ.get("BASE_URL")
    if not url:
        pytest.fail("BASE_URL environment variable is required (set by scripts/lever.py boot/checks)")
    return url.rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def _ui_ready(base_url):
    require_html_ui(base_url)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture(params=VIEWPORTS, ids=lambda w: f"{w}px")
def viewport_width(request):
    return request.param


@pytest.fixture
def page(browser, base_url, viewport_width):
    ctx = browser.new_context(viewport={"width": viewport_width, "height": 900})
    pg = ctx.new_page()
    yield pg
    ctx.close()
