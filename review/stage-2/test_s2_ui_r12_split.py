"""S2-UI-C8: split screen and preview (S2-R12)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.format_amount import format_amount
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(2)]

SPLIT_IDS = (
    "split-amount",
    "split-handles",
    "split-note",
    "split-submit",
    "split-preview",
)


def test_s2_ui_r12_split_testids(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/split")
    for tid in SPLIT_IDS:
        assert page.get_by_test_id(tid).count() >= 1, tid
    shot(page, "split_form", viewport_width)


def test_s2_ui_r12_split_preview_shares(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    page.goto(f"{base_url}/split")
    page.get_by_test_id("split-amount").fill("10.00")
    page.get_by_test_id("split-handles").fill("bob, cy")
    page.get_by_test_id("split-handles").blur()
    page.wait_for_timeout(400)
    shares = [500, 500]
    for handle, minor in zip(("bob", "cy"), shares, strict=True):
        tid = f"split-share-{handle}"
        assert page.get_by_test_id(tid).count() == 1, tid
        assert page.get_by_test_id(tid).inner_text().strip() == format_amount(minor, "EUR", 2)
    shot(page, "split_preview", viewport_width)
