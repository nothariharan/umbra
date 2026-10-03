"""Stage 2 — content negotiation and route reachability (no browser).

S2-R2 (routes), S2-R3 (content negotiation). Testids and visual product quality are
exercised in a real browser by test_ui_race.py.
"""
from __future__ import annotations

from attacklib2 import assert_status, describe, fixture2, new_key


def _accept(client, path, value):
    return client.get(path, headers={"Accept": value})


def test_required_routes_are_reachable(world):
    for path in ("/", "/requests", "/split", "/signup", "/login", "/authorizations"):
        resp = _accept(world.ada, path, "text/html")
        assert resp.status_code < 500, f"{path} errored: {describe(resp)}"
        assert resp.status_code != 404, f"required route {path} not found"
        if resp.status_code == 200:
            ctype = resp.headers.get("content-type", "")
            assert "text/html" in ctype.lower(), \
                f"{path} with Accept: text/html served {ctype!r}"


def test_requests_negotiates_html_vs_json(world):
    html = _accept(world.ada, "/requests", "text/html")
    assert html.status_code == 200, describe(html)
    assert "text/html" in html.headers.get("content-type", "").lower(), describe(html)

    data = _accept(world.ada, "/requests", "application/json")
    assert data.status_code == 200, describe(data)
    assert "application/json" in data.headers.get("content-type", "").lower(), describe(data)
    assert "requests" in data.json(), describe(data)

    default = world.ada.get("/requests")
    assert default.status_code == 200, describe(default)
    assert "application/json" in default.headers.get("content-type", "").lower(), describe(default)


def test_authorizations_negotiates_html_vs_json(world):
    html = _accept(world.ada, "/authorizations", "text/html")
    assert html.status_code == 200, describe(html)
    assert "text/html" in html.headers.get("content-type", "").lower(), describe(html)

    data = _accept(world.ada, "/authorizations", "application/json")
    assert data.status_code == 200, describe(data)
    assert "application/json" in data.headers.get("content-type", "").lower(), describe(data)
    assert "authorizations" in data.json(), describe(data)

    default = world.ada.get("/authorizations")
    assert default.status_code == 200, describe(default)
    assert "application/json" in default.headers.get("content-type", "").lower(), describe(default)


def test_json_api_routes_survive_an_html_accept_header(world):
    """Sending Accept: text/html to a JSON-only endpoint must not break the API."""
    for path in ("/me", "/activity"):
        resp = _accept(world.ada, path, "text/html")
        assert resp.status_code == 200, describe(resp)
        assert "application/json" in resp.headers.get("content-type", "").lower(), describe(resp)
