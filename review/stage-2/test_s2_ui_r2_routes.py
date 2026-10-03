"""S2-UI-C1: required routes reachable (S2-R2)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.ui import ROUTES, login, reset_base, require_html_ui, shot

pytestmark = [pytest.mark.stage(2)]


@pytest.mark.parametrize("path", ROUTES)
def test_s2_ui_r2_route_reachable(base_url, browser, path, viewport_width):
    require_html_ui(base_url)
    reset_base(base_url)
    page = browser.new_page(viewport={"width": viewport_width, "height": 900})
    page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
    assert page.url.rstrip("/").endswith(path.rstrip("/") or "")
    shot(page, f"route_{path.strip('/').replace('/', '_') or 'home'}", viewport_width)
    page.close()


def test_s2_ui_r2_signed_in_nav(base_url, browser, viewport_width):
    require_html_ui(base_url)
    reset_base(base_url)
    page = browser.new_page(viewport={"width": viewport_width, "height": 900})
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    for path in ("/", "/requests", "/split", "/authorizations"):
        page.goto(f"{base_url}{path}")
        assert page.locator("body").count() == 1
    shot(page, "signed_in_nav", viewport_width)
    page.close()
