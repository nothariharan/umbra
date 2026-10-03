"""S2-C6-C14: behavioural UI flows (S2-R7-R16). Expanded as Builder lands stage-2."""
from __future__ import annotations

import pytest

from lib import delivery

pytestmark = pytest.mark.stage(2)


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: pay resubmit/idempotency UI (S2-R8)")
def test_s2_c6_pay_form_no_double_submit_without_change():
    if not delivery.stage_dir_exists():
        pytest.skip("no stage-2")


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: post-action refresh (S2-R13)")
def test_s2_c11_balance_feed_refresh_after_pay():
    pass


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: wallet-refresh ordering (S2-R14)")
def test_s2_c12_wallet_refresh_latest_wins():
    pass


@pytest.mark.skip(reason="awaiting stage-2 SUBMIT: import upgrade session (S2-R16)")
def test_s2_c14_stage1_export_import_session_survives():
    pass
