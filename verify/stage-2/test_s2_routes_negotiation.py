"""S2-C2 routes (S2-R2), S2-C3 content negotiation (S2-R3)."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stage(2)

ROUTES = ("/", "/requests", "/split", "/signup", "/login", "/authorizations")


def test_s2_c2_required_routes_respond(base_url):
    for path in ROUTES:
        resp = __import__("httpx").get(f"{base_url}{path}", follow_redirects=True, timeout=5.0)
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"


def test_s2_c3_requests_html_vs_json(world):
    html = world.ada.get("/requests", headers={"Accept": "text/html"})
    assert html.status_code == 200
    assert "text/html" in html.headers.get("content-type", "").lower()
    js = world.ada.get("/requests", headers={"Accept": "application/json"})
    assert js.status_code == 200
    assert js.headers.get("content-type", "").startswith("application/json")
    assert isinstance(js.json(), dict)


def test_s2_c3_authorizations_html_vs_json(world):
    html = world.ada.get("/authorizations", headers={"Accept": "text/html"})
    assert html.status_code == 200
    assert "text/html" in html.headers.get("content-type", "").lower()
    js = world.ada.get("/authorizations")
    assert js.status_code == 200
    body = js.json()
    assert "authorizations" in body or isinstance(body, list)
