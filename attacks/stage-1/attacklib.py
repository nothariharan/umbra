"""Breaker attack harness for Pocketful stage 1.

Self-contained: only httpx, pytest and the standard library. Every suite reads the
service address from BASE_URL, exactly as the lever boots the submitted revision.
"""
from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8080")
REQUEST_TIMEOUT = 5.0
RESET_TIMEOUT = 10.0
PASSWORD = "correct horse"


def new_key() -> str:
    return uuid.uuid4().hex


class Client:
    """A tiny bearer-token client. token=None means unauthenticated."""

    def __init__(self, token: str | None = None, timeout: float = REQUEST_TIMEOUT):
        self._c = httpx.Client(base_url=BASE_URL.rstrip("/"), timeout=timeout)
        self.token = token

    def close(self) -> None:
        self._c.close()

    def request(self, method: str, path: str, *, json=None, headers=None,
                params=None, token=..., timeout=None) -> httpx.Response:
        hdrs = dict(headers or {})
        effective = self.token if token is ... else token
        if effective is not None:
            hdrs.setdefault("Authorization", f"Bearer {effective}")
        kwargs: dict = {"headers": hdrs}
        if json is not None:
            kwargs["json"] = json
        if params is not None:
            kwargs["params"] = params
        if timeout is not None:
            kwargs["timeout"] = timeout
        return self._c.request(method, path, **kwargs)

    def get(self, path: str, **kw) -> httpx.Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> httpx.Response:
        return self.request("POST", path, **kw)

    def login(self, email: str, password: str = PASSWORD) -> httpx.Response:
        resp = self.post("/auth/login", json={"email": email, "password": password},
                         token=None)
        if resp.status_code == 200:
            self.token = resp.json()["token"]
        return resp

    def me(self) -> dict:
        resp = self.get("/me")
        assert resp.status_code == 200, describe(resp)
        return resp.json()

    def balance(self) -> int:
        return self.me()["balance"]


def describe(resp: httpx.Response) -> str:
    body = resp.text
    if len(body) > 400:
        body = body[:400] + "..."
    return f"{resp.request.method} {resp.request.url.path} -> {resp.status_code} {body!r}"


def assert_status(resp: httpx.Response, expected: int) -> httpx.Response:
    assert resp.status_code == expected, f"expected {expected}. {describe(resp)}"
    return resp


def assert_status_in(resp: httpx.Response, expected: set[int]) -> httpx.Response:
    assert resp.status_code in expected, f"expected one of {expected}. {describe(resp)}"
    return resp


def error_code(resp: httpx.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        raise AssertionError(f"error body is not JSON. {describe(resp)}") from None
    assert isinstance(body, dict) and isinstance(body.get("error"), dict), \
        f"error body must be {{'error': {{'code': ...}}}}. {describe(resp)}"
    code = body["error"].get("code")
    assert isinstance(code, str) and code, f"error.code must be a string. {describe(resp)}"
    return code


def assert_error(resp: httpx.Response, status: int, code: str) -> httpx.Response:
    actual = error_code(resp) if 400 <= resp.status_code < 600 else None
    assert resp.status_code == status and actual == code, (
        f"expected {status} {code}, got {resp.status_code} {actual}. {describe(resp)}")
    return resp


def assert_no_5xx(resp: httpx.Response) -> httpx.Response:
    assert resp.status_code < 500, f"5xx is always a failure. {describe(resp)}"
    return resp


def race(fn, n: int) -> list:
    """Run fn(i) for i in range(n) as simultaneously as the OS allows."""
    barrier = threading.Barrier(n)

    def wrapped(i):
        barrier.wait()
        return fn(i)

    with ThreadPoolExecutor(max_workers=n) as ex:
        return list(ex.map(wrapped, range(n)))


def new_client() -> Client:
    return Client()


# --- fixture builders -------------------------------------------------------

def user(handle: str, balance: int, *, uid: str | None = None,
         email: str | None = None, display_name: str | None = None) -> dict:
    return {
        "id": uid or f"u_{handle}",
        "email": email or f"{handle}@example.com",
        "password": PASSWORD,
        "display_name": display_name or handle.title(),
        "handle": handle,
        "balance": balance,
    }


def fixture(*, users: list[dict] | None = None, currency: str = "EUR",
            minor_units: int | None = None, payments: list[dict] | None = None,
            requests: list[dict] | None = None,
            operators: list[str] | None = None) -> dict:
    units = {"EUR": 2, "JPY": 0, "BHD": 3}
    if users is None:
        users = [user("ada", 100_000), user("bob", 500),
                 user("cy", 250), user("op", 100_000, uid="u_op")]
        operators = operators if operators is not None else ["u_op"]
    return {
        "currency": currency,
        "minor_units": units[currency] if minor_units is None else minor_units,
        "users": users,
        "payments": payments or [],
        "requests": requests or [],
        "settlement_operator_ids": operators or [],
    }


def seeded_total(fx: dict) -> int:
    return sum(u["balance"] for u in fx["users"])


def do_reset(body: dict, expect: int = 204) -> httpx.Response:
    c = Client()
    try:
        return c.post("/_test/reset", json=body, timeout=RESET_TIMEOUT, token=None)
    finally:
        c.close()


def equal_split(amount: int, n: int) -> list[int]:
    base = amount // n if amount >= 0 else -((-amount) // n)
    remainder = amount - base * n
    return [base + (1 if i < remainder else 0) for i in range(n)]
