"""S2-UI-C7: requests screen (S2-R11)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.format_amount import format_amount
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(2)]


def test_s2_ui_r11_empty_requests(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/requests")
    assert page.get_by_test_id("empty-requests").count() >= 1
    shot(page, "empty_requests", viewport_width)


def test_s2_ui_r11_pending_incoming_actions(page, base_url, viewport_width):
    body = fx.fixture(
        requests=[
            {
                "request_id": "r_ui1",
                "requester_id": "u_bob",
                "payer_id": "u_ada",
                "amount": 500,
                "currency": "EUR",
                "note": "tea",
                "status": "pending",
                "created_at": "2026-09-24T12:00:00+00:00",
            }
        ]
    )
    reset_base(base_url, body)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/requests")
    assert page.get_by_test_id("incoming-list").count() >= 1
    assert page.get_by_test_id("outgoing-list").count() >= 1
    item = page.get_by_test_id("request-item-r_ui1")
    assert item.get_attribute("data-status") == "pending"
    assert page.get_by_test_id("request-amount-r_ui1").inner_text().strip() == format_amount(
        500, "EUR", 2
    )
    assert page.get_by_test_id("request-pay-r_ui1").count() == 1
    assert page.get_by_test_id("request-decline-r_ui1").count() == 1
    assert page.get_by_test_id("request-cancel-r_ui1").count() == 0
    shot(page, "incoming_pending", viewport_width)
