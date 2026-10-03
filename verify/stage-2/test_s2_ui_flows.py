"""S2-C6-C14: behavioural UI flows (S2-R7-R16)."""
from __future__ import annotations

import pytest

from lib import delivery

pytestmark = pytest.mark.stage(2)

pytest.importorskip("playwright.sync_api")


@pytest.mark.skipif(not delivery.stage_dir_exists(), reason="stage-2 not present")
def test_s2_c6_pay_form_no_double_submit_without_change(base_url):
    from playwright.sync_api import sync_playwright

    from lib import fixtures as fx

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/login")
        page.get_by_test_id("login-email").fill(fx.ADA["email"])
        page.get_by_test_id("login-password").fill(fx.ADA["password"])
        page.get_by_test_id("login-submit").click()
        page.get_by_test_id("pay-handle").fill("bob")
        page.get_by_test_id("pay-amount").fill("1.00")
        page.get_by_test_id("pay-submit").click()
        bal1 = page.get_by_test_id("wallet-balance").get_attribute("data-amount")
        page.get_by_test_id("pay-submit").click()
        bal2 = page.get_by_test_id("wallet-balance").get_attribute("data-amount")
        assert bal1 == bal2
        assert page.get_by_test_id("pay-error").count() == 0
        browser.close()


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: post-action refresh (S2-R13)")
def test_s2_c11_balance_feed_refresh_after_pay():
    pass


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: wallet-refresh ordering (S2-R14)")
def test_s2_c12_wallet_refresh_latest_wins():
    pass


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: import upgrade session (S2-R16)")
def test_s2_c14_stage1_export_import_session_survives():
    pass
