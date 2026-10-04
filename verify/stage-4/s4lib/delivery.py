"""Static checks on stage-4/ delivery artifacts (S4-R27, S4-U1)."""
from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
STAGE_DIR = REPO_ROOT / "stage-4"
STAGE3_DIR = REPO_ROOT / "stage-3"
SEALED_STAGE3_REV = "55207f5fd143"


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
        and p.name != "pocketful.exe"
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


def extends_sealed_stage3_baseline() -> tuple[bool, str]:
    if not STAGE3_DIR.is_dir():
        return False, "sealed stage-3 baseline missing under stage-3/"
    if not stage_dir_exists():
        return False, "stage-4 missing"
    return True, "ok"


IDEMPOTENT_WRITE_PATHS = (
    "POST /payments",
    "POST /requests",
    "POST /requests/{id}/pay",
    "POST /splits",
    "POST /settlements",
    "POST /authorizations",
    "POST /authorizations/{id}/capture",
    "POST /payments/{id}/corrections",
    "POST /payments/{payment_id}/refunds",
    "POST /correction-batches",
)
