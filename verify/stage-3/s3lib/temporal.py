"""RFC3339 helpers for stage-3 temporal queries."""
from __future__ import annotations

from datetime import datetime, timezone


def parse_instant(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("naive")
    return dt


def has_offset(value: str) -> bool:
    try:
        parse_instant(value)
    except ValueError:
        return False
    return True


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")
