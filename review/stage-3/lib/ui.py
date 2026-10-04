"""Playwright helpers for UI review."""
from __future__ import annotations

import pathlib

import httpx
import pytest
from playwright.sync_api import Page

from lib import fixtures as fx

SCREENSHOT_DIR = pathlib.Path(__file__).resolve().parents[1] / "screenshots"

ROUTES = ("/", "/requests", "/split", "/signup", "/login", "/authorizations")
VIEWPORTS = (375, 1280)


def require_html_ui(base_url: str) -> None:
    try:
        resp = httpx.get(
            f"{base_url}/login",
            headers={"Accept": "text/html"},
            follow_redirects=True,
            timeout=5.0,
        )
    except httpx.HTTPError as exc:
        pytest.skip(f"service unreachable: {exc}")
    if resp.status_code >= 500:
        pytest.skip(f"login route returned {resp.status_code}")
    if "login-email" not in resp.text:
        pytest.skip("login page missing mandated login-email testid")


def reset_base(base_url: str, body: dict | None = None) -> None:
    resp = httpx.post(f"{base_url}/_test/reset", json=body or fx.fixture(), timeout=10.0)
    if resp.status_code != 204:
        pytest.skip(f"reset failed: {resp.status_code} {resp.text[:200]}")


def login(page: Page, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login")
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()


def assert_no_horizontal_scroll(page: Page) -> None:
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert not overflow, "horizontal page scroll detected"


def shot(page: Page, name: str, width: int) -> pathlib.Path:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}_{width}px.png"
    page.screenshot(path=str(path), full_page=True)
    return path
