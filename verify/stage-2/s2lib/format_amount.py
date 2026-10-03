"""Format minor units as displayed in the UI (stage-2 spec)."""
from __future__ import annotations


def format_amount(minor: int, currency: str, minor_units: int) -> str:
    if minor_units == 0:
        return f"{minor} {currency}"
    whole, frac = divmod(minor, 10**minor_units)
    frac_s = str(frac).rjust(minor_units, "0")
    return f"{whole}.{frac_s} {currency}"
