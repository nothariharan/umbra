"""S2-C4..C13, C25..C26: mandated data-testid and key UI flows (S2-R4-R15, R28-R29)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stage(2)

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from s2lib import delivery  # noqa: E402
from s2lib import fixtures as fx  # noqa: E402


@pytest.fixture(scope="module")
def browser_base(base_url):
    if not delivery.stage_dir_exists():
        pytest.skip("stage-2 not built yet")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser, base_url
        browser.close()


def _login(page, base_url, email, password):
    page.goto(f"{base_url}/login")
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()
    page.get_by_test_id("current-user").wait_for(state="visible", timeout=10_000)


def test_s2_c4_home_wallet_and_pay_testids(browser_base):
    browser, base_url = browser_base
    page = browser.new_page(viewport={"width": 375, "height": 812})
    _login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/")
    page.get_by_test_id("wallet-balance").wait_for(state="visible", timeout=10_000)
    for tid in (
        "wallet-balance",
        "pay-handle",
        "pay-amount",
        "pay-note",
        "pay-visibility",
        "pay-submit",
        "request-handle",
        "request-amount",
        "request-note",
        "request-submit",
        "activity-list",
        "current-user",
        "current-handle",
        "logout-button",
        "wallet-refresh",
    ):
        assert page.get_by_test_id(tid).count() >= 1, tid
    page.close()


def test_s2_c5_signup_login_testids(browser_base):
    browser, base_url = browser_base
    page = browser.new_page()
    page.goto(f"{base_url}/signup")
    for tid in ("signup-email", "signup-password", "signup-display-name", "signup-submit"):
        assert page.get_by_test_id(tid).count() == 1
    page.goto(f"{base_url}/login")
    for tid in ("login-email", "login-password", "login-submit"):
        assert page.get_by_test_id(tid).count() == 1
    page.close()


def test_s2_c25_authorizations_screen_testids(browser_base):
    browser, base_url = browser_base
    page = browser.new_page()
    _login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/authorizations")
    for tid in (
        "wallet-available",
        "authorize-handle",
        "authorize-amount",
        "authorize-submit",
        "authorization-list",
        "empty-authorizations",
    ):
        assert page.get_by_test_id(tid).count() >= 1, tid
    page.close()
