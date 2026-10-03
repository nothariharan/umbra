"""Fixture builders for Pocketful Stage 1 verifier checks."""
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


def user(
    handle: str,
    balance: int,
    *,
    uid: str | None = None,
    email: str | None = None,
    display_name: str | None = None,
    password: str = "correct horse",
) -> dict:
    return {
        "id": uid or f"u_{handle}",
        "email": email or f"{handle}@example.com",
        "password": password,
        "display_name": display_name or handle.title(),
        "handle": handle,
        "balance": balance,
    }


def fixture(
    *,
    users: list[dict] | None = None,
    currency: str = "EUR",
    minor_units: int | None = None,
    payments: list[dict] | None = None,
    requests: list[dict] | None = None,
    settlement_operator_ids: list[str] | None = None,
) -> dict:
    body = {
        "currency": currency,
        "minor_units": CURRENCIES[currency] if minor_units is None else minor_units,
        "users": [ADA, BOB, CY] if users is None else users,
        "payments": payments or [],
        "requests": requests or [],
    }
    if settlement_operator_ids is not None:
        body["settlement_operator_ids"] = settlement_operator_ids
    return body


def seeded_total(fx: dict) -> int:
    return sum(u["balance"] for u in fx["users"])


def equal_split(amount: int, n: int) -> list[int]:
    base = amount // n if amount >= 0 else -((-amount) // n)
    remainder = amount - base * n
    return [base + (1 if i < remainder else 0) for i in range(n)]


def derive_handle(email: str) -> str:
    local = email.split("@", 1)[0].lower()
    out = []
    for ch in local:
        if "a" <= ch <= "z" or "0" <= ch <= "9" or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)[:20]
