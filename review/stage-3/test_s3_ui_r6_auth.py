"""S3-UI-C4: signup/login chrome and auth-error (S3-R30)."""
from __future__ import annotations

import pytest

from lib import fixtures as fx
from lib.ui import login, reset_base, shot

pytestmark = [pytest.mark.stage(3)]

SIGNUP_IDS = ("signup-email", "signup-password", "signup-display-name", "signup-submit")
LOGIN_IDS = ("login-email", "login-password", "login-submit")
SIGNED_IN_IDS = ("current-user", "current-handle", "logout-button")


def test_s3_ui_r6_signup_testids(page, base_url, viewport_width):
    reset_base(base_url)
    page.goto(f"{base_url}/signup")
    for tid in SIGNUP_IDS:
        assert page.get_by_test_id(tid).count() == 1, tid
    shot(page, "signup", viewport_width)


def test_s3_ui_r6_login_testids(page, base_url, viewport_width):
    reset_base(base_url)
    page.goto(f"{base_url}/login")
    for tid in LOGIN_IDS:
        assert page.get_by_test_id(tid).count() == 1, tid
    shot(page, "login", viewport_width)


def test_s3_ui_r6_signed_in_chrome(page, base_url, viewport_width):
    reset_base(base_url)
    login(page, base_url, fx.ADA["email"], fx.ADA["password"])
    for tid in SIGNED_IN_IDS:
        assert page.get_by_test_id(tid).count() >= 1, tid
    assert fx.ADA["display_name"] in page.get_by_test_id("current-user").inner_text()
    assert page.get_by_test_id("current-handle").inner_text().strip() == fx.ADA["handle"]
    shot(page, "signed_in_chrome", viewport_width)


def test_s3_ui_r6_auth_error_only_on_failure(page, base_url, viewport_width):
    reset_base(base_url)
    page.goto(f"{base_url}/login")
    assert page.get_by_test_id("auth-error").count() == 0
    page.get_by_test_id("login-email").fill("nobody@example.com")
    page.get_by_test_id("login-password").fill("wrong")
    page.get_by_test_id("login-submit").click()
    page.wait_for_timeout(500)
    assert page.get_by_test_id("auth-error").count() >= 1
    assert page.get_by_test_id("auth-error").inner_text().strip() != ""
    shot(page, "auth_error", viewport_width)
