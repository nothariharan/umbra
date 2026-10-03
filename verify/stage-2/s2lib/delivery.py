"""Static checks on stage-2/ delivery artifacts (S2-R31)."""
from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
STAGE_DIR = REPO_ROOT / "stage-2"
STAGE1_DIR = REPO_ROOT / "stage-1"


def stage_dir_exists() -> bool:
    return STAGE_DIR.is_dir()


def delivery_files_present() -> tuple[bool, str]:
    if not stage_dir_exists():
        return False, f"missing {STAGE_DIR}"
    dockerfile = STAGE_DIR / "Dockerfile"
    run_md = STAGE_DIR / "RUN.md"
    if not dockerfile.is_file():
        return False, "missing Dockerfile"
    if not run_md.is_file():
        return False, "missing RUN.md"
    sources = [
        p
        for p in STAGE_DIR.rglob("*")
        if p.is_file()
        and p.name not in ("Dockerfile", "RUN.md")
        and "__pycache__" not in p.parts
        and not p.suffix.endswith(".pyc")
    ]
    if not sources:
        return False, "no service source files besides Dockerfile and RUN.md"
    return True, "ok"


def run_md_single_command() -> tuple[bool, str]:
    run_md = STAGE_DIR / "RUN.md"
    if not run_md.is_file():
        return False, "RUN.md missing"
    text = run_md.read_text(encoding="utf-8")
    fences = re.findall(r"```(?:sh|bash|shell)?\s*\n(.*?)```", text, re.S | re.I)
    if len(fences) != 1:
        return False, f"expected exactly one fenced command block, found {len(fences)}"
    cmd = fences[0].strip()
    if not cmd or "\n\n" in cmd:
        return False, "RUN.md command block must be one command (no blank lines)"
    lower = cmd.lower()
    if "docker build" not in lower or "docker run" not in lower:
        return False, "RUN.md command must build and run via docker"
    return True, "ok"


def dockerfile_port_contract() -> tuple[bool, str]:
    dockerfile = STAGE_DIR / "Dockerfile"
    if not dockerfile.is_file():
        return False, "Dockerfile missing"
    text = dockerfile.read_text(encoding="utf-8")
    if "8080" not in text and "PORT" not in text:
        return False, "Dockerfile should expose PORT (default 8080)"
    return True, "ok"


def extends_stage1_baseline() -> tuple[bool, str]:
    if not STAGE1_DIR.is_dir():
        return False, "sealed stage-1 baseline missing under stage-1/"
    if not stage_dir_exists():
        return False, "stage-2 missing"
    return True, "ok"
