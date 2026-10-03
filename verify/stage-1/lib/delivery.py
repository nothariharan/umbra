"""Static checks on stage-1/ delivery artifacts (S1-R1, S1-R2, S1-R44)."""
from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
STAGE_DIR = REPO_ROOT / "stage-1"


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
    return True, cmd


def dockerfile_port_contract() -> tuple[bool, str]:
    dockerfile = STAGE_DIR / "Dockerfile"
    if not dockerfile.is_file():
        return False, "Dockerfile missing"
    text = dockerfile.read_text(encoding="utf-8")
    if "PORT" not in text:
        return False, "Dockerfile should reference PORT"
    return True, "ok"


def sources_listen_contract() -> tuple[bool, str]:
    if not stage_dir_exists():
        return False, "stage-1 missing"
    hits = []
    for path in STAGE_DIR.rglob("*"):
        if not path.is_file() or path.suffix in (".md", ".json"):
            continue
        if "__pycache__" in path.parts:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "0.0.0.0" in body and "PORT" in body:
            hits.append(str(path.relative_to(STAGE_DIR)))
    if not hits:
        return False, "no source references both 0.0.0.0 and PORT"
    return True, ",".join(hits[:3])
