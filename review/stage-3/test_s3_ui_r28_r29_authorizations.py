"""S3-UI-C9-C12: authorizations UI (S3-R30)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.format_amount import format_amount
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(3)]

AUTH_SCREEN_IDS = (
    "wallet-available",
    "authorize-handle",
    "authorize-amount",
    "authorize-note",
    "authorize-visibility",
    "authorize-submit",
    "authorization-list",
    "empty-authorizations",
)


def test_s3_ui_r28_authorizations_testids(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/authorizations")
    for tid in AUTH_SCREEN_IDS:
        assert page.get_by_test_id(tid).count() >= 1, tid
    avail = page.get_by_test_id("wallet-available")
    assert avail.get_attribute("data-amount") is not None
    assert page.get_by_test_id("empty-authorizations").is_visible()
    assert page.get_by_test_id("authorization-list").locator("[data-testid^='authorization-item-']").count() == 0
    shot(page, "authorizations_empty", viewport_width)


def test_s3_ui_r28_wallet_held_absent_without_hold(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/authorizations")
    assert page.get_by_test_id("wallet-held").count() == 0
    shot(page, "wallet_no_hold", viewport_width)


def test_s3_ui_r28_wallet_headline_with_hold(page, base_url, viewport_width):
    body = fx.fixture(
        authorizations=[
            {
                "id": "a_ui1",
                "from_user_id": "u_ada",
                "to_user_id": "u_bob",
                "amount": 2000,
                "note": "hold",
                "visibility": "private",
                "status": "open",
                "expires_at": "2099-09-24T13:20:00+00:00",
            }
        ]
    )
    reset_base(base_url, body)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/authorizations")
    assert page.get_by_test_id("wallet-held").count() >= 1
    held_minor = int(page.get_by_test_id("wallet-held").get_attribute("data-amount") or "0")
    assert held_minor == 2000
    avail_minor = int(page.get_by_test_id("wallet-available").get_attribute("data-amount") or "0")
    assert avail_minor == 10_000 - 2000
    assert page.get_by_test_id("wallet-available").inner_text().strip() == format_amount(
        avail_minor, "EUR", 2
    )
    shot(page, "wallet_with_hold", viewport_width)


def _seed_open_auth(base_url: str) -> None:
    body = fx.fixture(
        authorizations=[
            {
                "id": "a_ui2",
                "from_user_id": "u_ada",
                "to_user_id": "u_bob",
                "amount": 1000,
                "note": "",
                "visibility": "public",
                "status": "open",
                "expires_at": "2099-09-24T13:20:00+00:00",
            }
        ]
    )
    reset_base(base_url, body)


def test_s3_ui_r28_open_auth_item_fields(page, base_url, viewport_width):
    _seed_open_auth(base_url)
    login(page, base_url, fx.BOB["email"], fx.BOB["password"])
    page.goto(f"{base_url}/authorizations")
    assert page.get_by_test_id("empty-authorizations").count() == 0
    assert (
        page.get_by_test_id("authorization-amount-a_ui2").inner_text().strip()
        == format_amount(1000, "EUR", 2)
    )
    expires = page.get_by_test_id("authorization-expires-a_ui2").inner_text().strip()
    assert "2099-09-24T13:20:00" in expires or expires.endswith("+00:00")
    assert page.get_by_test_id("authorization-captured-a_ui2").count() == 0
    shot(page, "auth_item_fields", viewport_width)


def test_s3_ui_r28_authorize_error_insufficient(page, base_url, viewport_width):
    body = fx.fixture(
        authorizations=[
            {
                "id": "a_hold",
                "from_user_id": "u_ada",
                "to_user_id": "u_bob",
                "amount": 9900,
                "note": "",
                "visibility": "private",
                "status": "open",
                "expires_at": "2099-09-24T13:20:00+00:00",
            }
        ]
    )
    reset_base(base_url, body)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/authorizations")
    page.get_by_test_id("authorize-handle").fill("bob")
    page.get_by_test_id("authorize-amount").fill("50.00")
    page.get_by_test_id("authorize-submit").click()
    page.wait_for_timeout(500)
    err = page.get_by_test_id("authorize-error")
    assert err.count() >= 1
    assert err.is_visible()
    assert err.inner_text().strip() != ""
    shot(page, "authorize_error", viewport_width)


def test_s3_ui_r29_incoming_capture_controls(page, base_url, viewport_width):
    _seed_open_auth(base_url)
    login(page, base_url, fx.BOB["email"], fx.BOB["password"])
    page.goto(f"{base_url}/authorizations")
    item = page.get_by_test_id("authorization-item-a_ui2")
    assert item.count() == 1
    assert item.get_attribute("data-status") == "open"
    assert page.get_by_test_id("authorization-capture-a_ui2").count() == 1
    cap_amt = page.get_by_test_id("authorization-capture-amount-a_ui2")
    assert cap_amt.count() == 1
    assert cap_amt.input_value().replace(",", "") in ("10.00", "10")
    assert page.get_by_test_id("authorization-void-a_ui2").count() == 0
    shot(page, "incoming_open_auth", viewport_width)


def test_s3_ui_r29_captured_item_fields(page, base_url, viewport_width):
    body = fx.fixture(
        authorizations=[
            {
                "id": "a_cap",
                "from_user_id": "u_ada",
                "to_user_id": "u_bob",
                "amount": 2000,
                "note": "done",
                "visibility": "public",
                "status": "captured",
                "expires_at": "2099-09-24T13:20:00+00:00",
                "captured_amount": 2000,
            }
        ]
    )
    reset_base(base_url, body)
    login(page, base_url, fx.BOB["email"], fx.BOB["password"])
    page.goto(f"{base_url}/authorizations")
    item = page.get_by_test_id("authorization-item-a_cap")
    assert item.get_attribute("data-status") == "captured"
    assert (
        page.get_by_test_id("authorization-captured-a_cap").inner_text().strip()
        == format_amount(2000, "EUR", 2)
    )
    assert page.get_by_test_id("authorization-capture-a_cap").count() == 0
    assert page.get_by_test_id("authorization-void-a_cap").count() == 0
    shot(page, "captured_auth", viewport_width)


def test_s3_ui_r29_authorization_error_on_bad_capture(page, base_url, viewport_width):
    _seed_open_auth(base_url)
    login(page, base_url, fx.BOB["email"], fx.BOB["password"])
    page.goto(f"{base_url}/authorizations")
    page.get_by_test_id("authorization-capture-amount-a_ui2").fill("99.00")
    page.get_by_test_id("authorization-capture-a_ui2").click()
    page.wait_for_timeout(500)
    err = page.get_by_test_id("authorization-error")
    assert err.count() >= 1
    assert err.is_visible()
    assert err.inner_text().strip() != ""
    shot(page, "authorization_error", viewport_width)


def test_s3_ui_r29_outgoing_void_control(browser, base_url, viewport_width):
    _seed_open_auth(base_url)
    page = browser.new_page(viewport={"width": viewport_width, "height": 900})
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/authorizations")
    assert page.get_by_test_id("authorization-void-a_ui2").count() == 1
    assert page.get_by_test_id("authorization-capture-a_ui2").count() == 0
    shot(page, "outgoing_open_auth", viewport_width)
    page.close()
