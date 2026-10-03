"""S1-C1 S1-C2 S1-C3: delivery artifacts and listen/docker static contract."""
from __future__ import annotations

import pytest

from lib import delivery

pytestmark = pytest.mark.stage(1)


def test_s1_c1_stage1_has_source_dockerfile_and_run_md():
    ok, detail = delivery.delivery_files_present()
    if not delivery.stage_dir_exists():
        pytest.skip(f"stage-1 not present yet ({detail}); run after Builder SUBMIT")
    assert ok, detail


def test_s1_c2_run_md_documents_one_build_and_start_command():
    if not delivery.stage_dir_exists():
        pytest.skip("stage-1 not present yet")
    ok, detail = delivery.run_md_single_command()
    assert ok, detail


def test_s1_c3_dockerfile_and_sources_reference_port_binding():
    if not delivery.stage_dir_exists():
        pytest.skip("stage-1 not present yet")
    ok_d, msg_d = delivery.dockerfile_port_contract()
    ok_s, msg_s = delivery.sources_listen_contract()
    assert ok_d, msg_d
    assert ok_s, msg_s
