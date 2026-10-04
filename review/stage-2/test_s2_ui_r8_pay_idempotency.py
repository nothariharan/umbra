"""S2-UI-C13: pay form idempotency UI (S2-R8)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(2)]


def test_s2_ui_r8_pay_no_double_submit_without_change(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.get_by_test_id("current-user").wait_for(state="visible", timeout=10_000)
    page.goto(f"{base_url}/")
    page.get_by_test_id("pay-handle").wait_for(state="visible", timeout=10_000)
    page.get_by_test_id("pay-handle").fill("bob")
    page.get_by_test_id("pay-amount").fill("1.00")
    page.get_by_test_id("pay-submit").click()
    page.wait_for_function(
        """() => {
            const el = document.querySelector('[data-testid="wallet-balance"]');
            return el && el.getAttribute('data-amount') !== '10000';
        }""",
        timeout=10_000,
    )
    bal1 = page.get_by_test_id("wallet-balance").get_attribute("data-amount")
    page.get_by_test_id("pay-submit").click()
    bal2 = page.get_by_test_id("wallet-balance").get_attribute("data-amount")
    assert bal1 == bal2
    assert page.get_by_test_id("pay-error").count() == 0
    shot(page, "pay_idempotent_resubmit", viewport_width)
