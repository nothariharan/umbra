"""S3-UI-C2/C5: home testids, wallet, pay flows (S3-R30)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.format_amount import format_amount
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(3)]

HOME_IDS = (
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
    "wallet-refresh",
)


def test_s3_ui_r4_home_mandated_testids(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/")
    for tid in HOME_IDS:
        assert page.get_by_test_id(tid).count() >= 1, tid
    shot(page, "home_testids", viewport_width)


def test_s3_ui_r7_wallet_balance_format(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/")
    bal = page.get_by_test_id("wallet-balance")
    minor = int(bal.get_attribute("data-amount") or "0")
    expected = format_amount(minor, "EUR", 2)
    assert bal.inner_text().strip() == expected
    shot(page, "wallet_balance", viewport_width)


def test_s3_ui_r7_pay_visibility_options(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/")
    opts = page.get_by_test_id("pay-visibility").locator("option")
    values = {opts.nth(i).get_attribute("value") for i in range(opts.count())}
    assert values == {"public", "private"}
    shot(page, "pay_visibility", viewport_width)


def test_s3_ui_r7_pay_amount_rejects_extra_decimals(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/")
    page.get_by_test_id("pay-handle").fill("bob")
    page.get_by_test_id("pay-amount").fill("15.005")
    page.get_by_test_id("pay-submit").click()
    page.wait_for_timeout(300)
    assert page.get_by_test_id("pay-error").count() >= 1
    assert page.get_by_test_id("pay-error").inner_text().strip() != ""
    shot(page, "pay_validation_error", viewport_width)
