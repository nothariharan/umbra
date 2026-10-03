"""Async Playwright helpers for the stage-2 UI race attacks.

The UI suite must drive a real browser: races between out-of-order reads and a
lost write response only exist client-side. Each test runs inside asyncio.run().
"""
from __future__ import annotations

import os

import httpx
from playwright.async_api import async_playwright

from attacklib2 import PASSWORD

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8080").rstrip("/")


async def with_page(fn, *, width: int = 1280, height: int = 900):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": width, "height": height})
        page = await context.new_page()
        try:
            return await fn(page)
        finally:
            await context.close()
            await browser.close()


async def sign_in(page, handle: str, goto: str | None = "/"):
    await page.goto(f"{BASE_URL}/login")
    await page.get_by_test_id("login-email").fill(f"{handle}@example.com")
    await page.get_by_test_id("login-password").fill(PASSWORD)
    await page.get_by_test_id("login-submit").click()
    await page.get_by_test_id("current-user").wait_for(timeout=15_000)
    if goto is not None:
        await page.goto(f"{BASE_URL}{goto}")


async def api_call(method: str, path: str, *, token: str | None = None, json=None,
                   headers=None) -> httpx.Response:
    hdrs = dict(headers or {})
    if token:
        hdrs.setdefault("Authorization", f"Bearer {token}")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        return await client.request(method, path, json=json, headers=hdrs)


async def login_token(handle: str) -> str:
    resp = await api_call("POST", "/auth/login",
                          json={"email": f"{handle}@example.com", "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


async def reset_fixture(body: dict) -> None:
    resp = await api_call("POST", "/_test/reset", json=body)
    assert resp.status_code == 204, resp.text


def amount_attr(locator):
    return locator.get_attribute("data-amount")


async def wait_amount(page, testid: str, value: str, timeout: float = 8_000):
    loc = page.get_by_test_id(testid)
    await loc.wait_for(timeout=timeout)
    for _ in range(int(timeout / 100)):
        if await loc.get_attribute("data-amount") == value:
            return
        await page.wait_for_timeout(100)
    got = await loc.get_attribute("data-amount")
    raise AssertionError(f"{testid} data-amount is {got!r}, expected {value!r}")