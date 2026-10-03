"""S2-UI-C3: no horizontal scroll at 375px and desktop (S2-R5)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.ui import ROUTES, assert_no_horizontal_scroll, login, reset_base, shot

pytestmark = [pytest.mark.stage(2)]


@pytest.mark.parametrize("path", ROUTES)
def test_s2_ui_r5_no_horizontal_scroll(page, base_url, path, viewport_width):
    reset_base(base_url)
    if path in ("/login", "/signup"):
        page.goto(f"{base_url}{path}")
    else:
        login(page, base_url, fx.ADA["email"], fx.ADA["password"])
        page.goto(f"{base_url}{path}")
    assert_no_horizontal_scroll(page)
    shot(page, f"layout_{path.strip('/').replace('/', '_') or 'home'}", viewport_width)
