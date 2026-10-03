"""S2-UI-C6: activity feed testids (S2-R10)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.format_amount import format_amount
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(2)]


def test_s2_ui_r10_empty_activity(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.CY["email"], fx.CY["password"])
    page.goto(f"{base_url}/")
    assert page.get_by_test_id("empty-activity").count() >= 1
    assert page.get_by_test_id("activity-list").count() == 0
    shot(page, "empty_activity", viewport_width)


def test_s2_ui_r10_activity_item_fields(page, base_url, viewport_width):
    fx_body = fx.fixture(
        payments=[
            {
                "payment_id": "p_ui1",
                "from_user_id": "u_ada",
                "to_user_id": "u_bob",
                "amount": 1500,
                "currency": "EUR",
                "note": "lunch",
                "visibility": "public",
                "created_at": "2026-09-24T12:00:00+00:00",
            }
        ]
    )
    reset_base(base_url, fx_body)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/")
    item = page.get_by_test_id("activity-item-p_ui1")
    assert item.count() == 1
    assert item.get_attribute("data-visibility") == "public"
    parties = page.get_by_test_id("activity-parties-p_ui1").inner_text()
    assert "ada" in parties and "bob" in parties
    assert page.get_by_test_id("activity-amount-p_ui1").inner_text().strip() == format_amount(
        1500, "EUR", 2
    )
    assert page.get_by_test_id("activity-note-p_ui1").inner_text() == "lunch"
    shot(page, "activity_item", viewport_width)
