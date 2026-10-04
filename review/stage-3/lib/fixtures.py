"""Fixture builders for Pocketful Stage 2 UI review."""
from __future__ import annotations

CURRENCIES = {"EUR": 2, "JPY": 0, "BHD": 3}

ADA = {
    "id": "u_ada",
    "email": "ada@example.com",
    "password": "correct horse",
    "display_name": "Ada",
    "handle": "ada",
    "balance": 10_000,
}
BOB = {
    "id": "u_bob",
    "email": "bob@example.com",
    "password": "correct horse",
    "display_name": "Bob",
    "handle": "bob",
    "balance": 2_500,
}
CY = {
    "id": "u_cy",
    "email": "cy@example.com",
    "password": "correct horse",
    "display_name": "Cy",
    "handle": "cy",
    "balance": 500,
}


def fixture(
    *,
    users: list[dict] | None = None,
    currency: str = "EUR",
    minor_units: int | None = None,
    payments: list[dict] | None = None,
    requests: list[dict] | None = None,
    authorization_ttl_seconds: int = 600,
    authorizations: list[dict] | None = None,
) -> dict:
    body = {
        "currency": currency,
        "minor_units": CURRENCIES[currency] if minor_units is None else minor_units,
        "users": [ADA, BOB, CY] if users is None else users,
        "payments": payments or [],
        "requests": requests or [],
        "authorization_ttl_seconds": authorization_ttl_seconds,
    }
    if authorizations is not None:
        body["authorizations"] = authorizations
    return body
