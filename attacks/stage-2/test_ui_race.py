"""Stage 2 — browser UI races and required interactions (Playwright).

S2-R8 (pay-form idempotency), S2-R13 (refresh after a write), S2-R14 (latest refresh
wins), S2-R15 (competing clients and uncertain outcomes), S2-R28/R29 (authorization UI).
Each sync test drives a real Chromium page via asyncio.run().
"""
from __future__ import annotations

import asyncio

from attacklib2 import authz, fixture2, future_iso, new_key
from uilab import (
    api_call,
    login_token,
    reset_fixture,
    sign_in,
    wait_amount,
    with_page,
)


def test_pay_form_unchanged_resubmit_does_not_double_pay():
    async def main(page):
        await reset_fixture(fixture2())
        await sign_in(page, "ada", goto="/")
        await wait_amount(page, "wallet-balance", "100000")

        await page.get_by_test_id("pay-handle").fill("bob")
        await page.get_by_test_id("pay-amount").fill("15.00")
        await page.get_by_test_id("pay-note").fill("lunch")
        await page.get_by_test_id("pay-submit").click()
        await wait_amount(page, "wallet-balance", "98500")
        await page.wait_for_timeout(500)
        assert await page.locator('[data-testid^="activity-item-"]').count() == 1
        # the form keeps its values after success
        assert await page.get_by_test_id("pay-handle").input_value() == "bob"
        assert await page.get_by_test_id("pay-amount").input_value() == "15.00"

        # resubmitting without a change must not send another payment
        await page.get_by_test_id("pay-submit").click()
        await page.wait_for_timeout(1500)
        await wait_amount(page, "wallet-balance", "98500")
        assert await page.locator('[data-testid^="activity-item-"]').count() == 1
        assert await page.get_by_test_id("pay-error").count() == 0

        # changing a field makes the next submission a new payment
        await page.get_by_test_id("pay-amount").fill("1.00")
        await page.get_by_test_id("pay-submit").click()
        await wait_amount(page, "wallet-balance", "98400")

    asyncio.run(with_page(main))


def test_lost_payment_response_is_uncertain_then_retry_moves_money_once():
    async def main(page):
        await reset_fixture(fixture2())
        await sign_in(page, "ada", goto="/")
        await wait_amount(page, "wallet-balance", "100000")

        state = {"n": 0}

        async def handler(route):
            state["n"] += 1
            if state["n"] == 1:
                await route.fetch()      # the server commits
                await route.abort()      # ... but the browser never sees the response
            else:
                await route.continue_()

        await page.route("**/payments", handler)
        await page.get_by_test_id("pay-handle").fill("bob")
        await page.get_by_test_id("pay-amount").fill("1.00")
        await page.get_by_test_id("pay-submit").click()

        uncertain = page.get_by_test_id("pay-uncertain")
        await uncertain.wait_for(timeout=8_000)
        assert (await uncertain.inner_text()).strip() != "", "pay-uncertain must be nonempty"
        assert await page.get_by_test_id("pay-error").count() == 0, \
            "an unknown outcome is not a confirmed rejection"

        # unchanged retry with the same key and body
        await page.get_by_test_id("pay-submit").click()
        await uncertain.wait_for(state="detached", timeout=10_000)
        await wait_amount(page, "wallet-balance", "99000")
        assert await page.locator('[data-testid^="activity-item-"]').count() == 1

        bob = await login_token("bob")
        feed = await api_call("GET", "/activity", token=bob)
        assert len(feed.json()["payments"]) == 1, "money must move exactly once"

    asyncio.run(with_page(main))


def test_remote_spend_shows_pay_error_and_refreshes_without_clearing_form():
    async def main(page):
        await reset_fixture(fixture2())
        await sign_in(page, "ada", goto="/")
        await wait_amount(page, "wallet-balance", "100000")

        ada = await login_token("ada")
        spent = await api_call("POST", "/payments", token=ada,
                               json={"to_handle": "bob", "amount": 99_000},
                               headers={"Idempotency-Key": new_key()})
        assert spent.status_code == 201, spent.text

        await page.get_by_test_id("pay-handle").fill("bob")
        await page.get_by_test_id("pay-amount").fill("50.00")
        await page.get_by_test_id("pay-submit").click()
        await page.get_by_test_id("pay-error").wait_for(timeout=8_000)
        await wait_amount(page, "wallet-balance", "1000")
        assert await page.get_by_test_id("pay-handle").input_value() == "bob"
        assert await page.get_by_test_id("pay-amount").input_value() == "50.00"

    asyncio.run(with_page(main))


def test_remotely_cancelled_request_shows_error_and_drops_pay_button():
    async def main(page):
        await reset_fixture(fixture2())
        bob = await login_token("bob")
        made = await api_call("POST", "/requests", token=bob,
                              json={"payer_handle": "ada", "amount": 500},
                              headers={"Idempotency-Key": new_key()})
        assert made.status_code == 201, made.text
        rid = made.json()["request_id"]

        await sign_in(page, "ada", goto="/requests")
        await page.get_by_test_id(f"request-pay-{rid}").wait_for(timeout=8_000)

        cancelled = await api_call("POST", f"/requests/{rid}/cancel", token=bob)
        assert cancelled.status_code == 200, cancelled.text

        await page.get_by_test_id(f"request-pay-{rid}").click()
        await page.get_by_test_id("request-error").wait_for(timeout=8_000)
        await page.get_by_test_id(f"request-pay-{rid}").wait_for(state="detached",
                                                                 timeout=8_000)
        status = await page.get_by_test_id(f"request-item-{rid}").get_attribute("data-status")
        assert status == "cancelled", f"stale pay button survived; status={status}"

    asyncio.run(with_page(main))


def test_paying_a_request_refreshes_the_list():
    async def main(page):
        await reset_fixture(fixture2())
        bob = await login_token("bob")
        made = await api_call("POST", "/requests", token=bob,
                              json={"payer_handle": "ada", "amount": 500},
                              headers={"Idempotency-Key": new_key()})
        assert made.status_code == 201, made.text
        rid = made.json()["request_id"]

        await sign_in(page, "ada", goto="/requests")
        await page.get_by_test_id(f"request-pay-{rid}").click()
        item = page.get_by_test_id(f"request-item-{rid}")
        for _ in range(80):
            if await item.get_attribute("data-status") == "paid":
                break
            await page.wait_for_timeout(100)
        assert await item.get_attribute("data-status") == "paid", "list did not refresh"
        assert await page.get_by_test_id(f"request-pay-{rid}").count() == 0
        assert await page.get_by_test_id("request-error").count() == 0

    asyncio.run(with_page(main))


def test_wallet_refresh_latest_wins_over_a_delayed_read():
    async def main(page):
        await reset_fixture(fixture2())
        await sign_in(page, "ada", goto="/")
        await wait_amount(page, "wallet-balance", "100000")
        await page.get_by_test_id("pay-note").fill("keep me")

        state = {"n": 0}

        async def handler(route):
            state["n"] += 1
            if state["n"] == 1:
                resp = await route.fetch()
                state["fetched"] = True
                await asyncio.sleep(1.5)
                await route.fulfill(response=resp)
            else:
                await route.continue_()

        await page.route("**/me", handler)
        await page.get_by_test_id("wallet-refresh").click()
        for _ in range(50):
            if state.get("fetched"):
                break
            await page.wait_for_timeout(100)
        assert state.get("fetched"), "the refresh button did not issue a /me read"

        bob = await login_token("bob")
        paid = await api_call("POST", "/payments", token=bob,
                              json={"to_handle": "ada", "amount": 1_000},
                              headers={"Idempotency-Key": new_key()})
        assert paid.status_code == 201, paid.text

        await page.get_by_test_id("wallet-refresh").click()
        for _ in range(50):
            if state["n"] >= 2:
                break
            await page.wait_for_timeout(100)
        assert state["n"] >= 2, "the refresh button did not issue a read"

        # the stale first response lands last and must not overwrite the newer one
        await page.wait_for_timeout(2_000)
        await wait_amount(page, "wallet-balance", "101000")
        assert await page.get_by_test_id("pay-note").input_value() == "keep me"

    asyncio.run(with_page(main))


def test_authorizations_page_shows_available_headline_and_permitted_controls():
    async def main(page):
        await reset_fixture(fixture2(authorizations=[
            authz("a_seed", "u_ada", "u_bob", 2_000, expires_at=future_iso(7200))]))
        await sign_in(page, "ada", goto="/authorizations")

        await wait_amount(page, "wallet-available", "98000")
        await wait_amount(page, "wallet-balance", "100000")
        await wait_amount(page, "wallet-held", "2000")
        for tid in ("authorize-handle", "authorize-amount", "authorize-note",
                    "authorize-visibility", "authorize-submit"):
            assert await page.get_by_test_id(tid).count() >= 1, f"missing {tid}"

        item = page.get_by_test_id("authorization-item-a_seed")
        await item.wait_for(timeout=8_000)
        assert await item.get_attribute("data-status") == "open"
        assert await page.get_by_test_id("authorization-void-a_seed").count() == 1, \
            "the payer must see a void control on an open outgoing authorization"
        assert await page.get_by_test_id("authorization-capture-a_seed").count() == 0, \
            "the payer must not see a capture control"

        # creating a hold through the UI updates the headline
        await page.get_by_test_id("authorize-handle").fill("bob")
        await page.get_by_test_id("authorize-amount").fill("5.00")
        await page.get_by_test_id("authorize-submit").click()
        await wait_amount(page, "wallet-held", "2500")
        assert await page.get_by_test_id("authorization-error").count() == 0

    asyncio.run(with_page(main))


def test_authorization_list_testids_capture_prefill_and_error():
    async def main(page):
        expires = future_iso(7200)
        await reset_fixture(fixture2(authorizations=[
            authz("a_cap", "u_ada", "u_bob", 4_000, status="captured",
                  captured_amount=4_000, expires_at=expires),
            authz("a_open", "u_cy", "u_ada", 1_500, expires_at=expires),
        ]))
        await sign_in(page, "ada", goto="/authorizations")

        cap = page.get_by_test_id("authorization-item-a_cap")
        await cap.wait_for(timeout=8_000)
        assert await cap.get_attribute("data-status") == "captured"
        assert await page.get_by_test_id("authorization-captured-a_cap").count() == 1, \
            "authorization-captured must be present on a captured authorization"

        token = await login_token("ada")
        listing = await api_call("GET", "/authorizations", token=token)
        server_expires = next(a["expires_at"] for a in listing.json()["authorizations"]
                              if a["authorization_id"] == "a_cap")
        assert await page.get_by_test_id("authorization-expires-a_cap").inner_text() == \
            server_expires, "authorization-expires must echo the API expires_at"

        # an incoming open authorization offers a prefilled capture amount
        amount = page.get_by_test_id("authorization-capture-amount-a_open")
        await amount.wait_for(timeout=8_000)
        assert (await amount.input_value()) == "15.00", \
            "the capture input must be prefilled with the remaining decimal amount"

        # over-capturing is refused and surfaces authorization-error
        await amount.fill("20.00")
        await page.get_by_test_id("authorization-capture-a_open").click()
        await page.get_by_test_id("authorization-error").wait_for(timeout=8_000)

    asyncio.run(with_page(main))


def test_empty_authorizations_state():
    async def main(page):
        await reset_fixture(fixture2())
        await sign_in(page, "op", goto="/authorizations")
        await page.get_by_test_id("empty-authorizations").wait_for(timeout=8_000)
        assert await page.locator('[data-testid^="authorization-item-"]').count() == 0

    asyncio.run(with_page(main))


def test_receiver_sees_capture_not_void_and_decimal_validation():
    async def main(page):
        await reset_fixture(fixture2(authorizations=[
            authz("a_seed", "u_ada", "u_bob", 2_000, expires_at=future_iso(7200))]))
        await sign_in(page, "bob", goto="/authorizations")

        item = page.get_by_test_id("authorization-item-a_seed")
        await item.wait_for(timeout=8_000)
        assert await page.get_by_test_id("authorization-capture-a_seed").count() == 1, \
            "the receiver must see a capture control"
        assert await page.get_by_test_id("authorization-void-a_seed").count() == 0

        # a decimal with more places than minor_units must not be submitted
        before = await page.locator('[data-testid^="authorization-item-"]').count()
        await page.get_by_test_id("authorize-handle").fill("cy")
        await page.get_by_test_id("authorize-amount").fill("1.005")
        await page.get_by_test_id("authorize-submit").click()
        await page.get_by_test_id("authorize-error").wait_for(timeout=8_000)
        after = await page.locator('[data-testid^="authorization-item-"]').count()
        assert before == after, "an invalid decimal created a hold"

    asyncio.run(with_page(main))
