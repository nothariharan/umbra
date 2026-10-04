"""S2-C13 / S2-R15: competing clients UI (pay-error, stale pay control, pay-uncertain)."""
from __future__ import annotations

import pytest

from s2lib import delivery
from s2lib import fixtures as fx
from s2lib.http import assert_status, new_key

pytestmark = pytest.mark.stage(2)

pytest.importorskip("playwright.sync_api")


def _login(page, base_url: str, email: str, password: str) -> None:
    page.goto(f"{base_url}/login")
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()
    page.get_by_test_id("current-user").wait_for(state="visible", timeout=15_000)


def _wait_amount(page, testid: str, amount: str, *, timeout_ms: int = 10_000) -> None:
    loc = page.get_by_test_id(testid)
    for _ in range(timeout_ms // 100):
        if loc.get_attribute("data-amount") == amount:
            return
        page.wait_for_timeout(100)
    got = loc.get_attribute("data-amount")
    assert got == amount, f"{testid} data-amount expected {amount}, got {got}"


def _rich_fixture(reset):
    ada = {**fx.ADA, "balance": 100_000}
    reset(fx.fixture(users=[ada, fx.BOB, fx.CY]))


@pytest.mark.skipif(not delivery.stage_dir_exists(), reason="stage-2 not present")
def test_s2_c13_competing_clients_ui(base_url, reset, api):
    from playwright.sync_api import sync_playwright

    _rich_fixture(reset)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Remote spend -> pay-error, balance refresh, form inputs kept
        _login(page, base_url, fx.ADA["email"], fx.ADA["password"])
        page.goto(f"{base_url}/")
        _wait_amount(page, "wallet-balance", "100000")
        ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
        spent = ada.post(
            "/payments",
            json={"to_handle": "bob", "amount": 99_000},
            idempotency_key=new_key(),
        )
        assert_status(spent, 201)
        page.goto(f"{base_url}/")
        page.get_by_test_id("pay-handle").fill("bob")
        page.get_by_test_id("pay-amount").fill("50.00")
        page.get_by_test_id("pay-submit").click()
        page.get_by_test_id("pay-error").wait_for(timeout=8_000)
        _wait_amount(page, "wallet-balance", "1000")
        assert page.get_by_test_id("pay-handle").input_value() == "bob"
        assert page.get_by_test_id("pay-amount").input_value() == "50.00"

        # Remote cancel -> stale request pay control removed after error
        _rich_fixture(reset)
        bob = api().authenticate(fx.BOB["email"], fx.BOB["password"])
        made = bob.post(
            "/requests",
            json={"payer_handle": "ada", "amount": 500},
            idempotency_key=new_key(),
        )
        assert_status(made, 201)
        rid = made.json()["request_id"]
        page.goto(f"{base_url}/login")
        _login(page, base_url, fx.ADA["email"], fx.ADA["password"])
        page.goto(f"{base_url}/requests")
        page.get_by_test_id(f"request-pay-{rid}").wait_for(timeout=8_000)
        cancelled = bob.post(f"/requests/{rid}/cancel")
        assert_status(cancelled, 200)
        page.get_by_test_id(f"request-pay-{rid}").click()
        page.get_by_test_id("request-error").wait_for(timeout=8_000)
        page.get_by_test_id(f"request-pay-{rid}").wait_for(state="detached", timeout=8_000)
        status = page.get_by_test_id(f"request-item-{rid}").get_attribute("data-status")
        assert status == "cancelled"

        # Lost payment response -> pay-uncertain then same idempotency retry pays once
        _rich_fixture(reset)
        page.goto(f"{base_url}/login")
        _login(page, base_url, fx.ADA["email"], fx.ADA["password"])
        page.goto(f"{base_url}/")
        _wait_amount(page, "wallet-balance", "100000")
        state = {"n": 0}

        def payment_route(route):
            state["n"] += 1
            if state["n"] == 1:
                route.fetch()
                route.abort()
            else:
                route.continue_()

        page.route("**/payments", payment_route)
        page.get_by_test_id("pay-handle").fill("bob")
        page.get_by_test_id("pay-amount").fill("1.00")
        page.get_by_test_id("pay-submit").click()
        uncertain = page.get_by_test_id("pay-uncertain")
        uncertain.wait_for(timeout=8_000)
        assert uncertain.inner_text().strip() != ""
        assert page.get_by_test_id("pay-error").count() == 0
        page.get_by_test_id("pay-submit").click()
        uncertain.wait_for(state="detached", timeout=10_000)
        _wait_amount(page, "wallet-balance", "99900")
        assert page.locator('[data-testid^="activity-item-"]').count() == 1
        bob_client = api().authenticate(fx.BOB["email"], fx.BOB["password"])
        feed = bob_client.get("/activity")
        assert_status(feed, 200)
        assert len(feed.json()["payments"]) == 1

        browser.close()
