"""Part 2/2 spec refinements for S3-C16..C28 (revisions, known_at, snapshots, import, holds)."""
from __future__ import annotations

import concurrent.futures

import httpx
import pytest

from s3lib import fixtures as fx
from s3lib.http import Api, assert_error, assert_status, new_key

pytestmark = pytest.mark.stage(3)


def test_s3_c19_revisions_shape_auth_and_public_third_party(reset, world, api, base_url):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "public",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    anon = Api(base_url, token=None)
    try:
        assert anon.get("/payments/pay1/revisions").status_code == 401
    finally:
        anon.close()
    body = assert_status(world.ada.get("/payments/pay1/revisions"), 200).json()
    assert "revisions" in body
    assert body["revisions"][0]["reason"] == ""
    assert_error(world.cy.get("/payments/pay1/revisions"), 404, "not_found")


def test_s3_c19_idempotent_payment_response_unchanged_after_correction(reset, world, pay):
    fx_body = fx.fixture()
    reset(fx_body)
    key = new_key()
    first = assert_status(pay(amount=77, key=key), 201).json()
    pid = first["payment_id"]
    assert_status(
        world.ada.post(
            f"/payments/{pid}/corrections",
            json={
                "expected_revision": 1,
                "amount": 70,
                "effective_at": "2026-09-20T12:00:00+00:00",
                "reason": "adj",
            },
            idempotency_key=new_key(),
        ),
        201,
    )
    replay = assert_status(pay(amount=77, key=key), 200).json()
    assert replay["payment_id"] == first["payment_id"]
    assert replay["amount"] == first["amount"]


def test_s3_c20_known_at_invalid_and_future(reset, world, me_wallet):
    assert_error(world.ada.get("/me", params={"known_at": "bad"}), 422, "validation_failed")
    future = "2099-06-01T00:00:00+00:00"
    me = me_wallet(world.ada, known_at=future)
    assert me.get("known_at") == future


def test_s3_c20_payment_omitted_when_not_yet_known(reset, world):
    fx_body = fx.fixture()
    reset(fx_body)
    pay_resp = assert_status(
        world.ada.post("/payments", json={"to_handle": "bob", "amount": 50}, idempotency_key=new_key()),
        201,
    )
    pid = pay_resp.json()["payment_id"]
    early = "2020-01-01T00:00:00+00:00"
    st = assert_status(world.ada.get("/statement", params={"known_at": early}), 200).json()
    assert all(e["payment"]["payment_id"] != pid for e in st["entries"])


def test_s3_c21_statement_entry_includes_revision_times(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    assert_status(
        world.ada.post(
            "/payments/pay1/corrections",
            json={
                "expected_revision": 1,
                "amount": 450,
                "effective_at": "2026-09-19T10:00:00+00:00",
                "reason": "backdate",
            },
            idempotency_key=new_key(),
        ),
        201,
    )
    st = assert_status(
        world.ada.get("/statement", params={"known_at": "2026-09-21T00:00:00+00:00"}),
        200,
    ).json()
    assert len(st["entries"]) == 1
    entry = st["entries"][0]
    for field in ("revision", "effective_at", "recorded_at"):
        assert field in entry
    assert entry["payment"]["amount"] == 450
    eff_times = [e["effective_at"] for e in st["entries"]]
    assert eff_times == sorted(eff_times)


def test_s3_c22_snapshot_has_more_and_unknown_token(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": f"p{i}",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 10 + i,
                "visibility": "private",
                "created_at": f"2026-09-20T{10+i:02d}:00:00+00:00",
            }
            for i in range(3)
        ]
    )
    reset(fx_body)
    first = assert_status(world.ada.get("/statement"), 200).json()
    token = first["snapshot"]
    page0 = assert_status(
        world.ada.get("/statement", params={"snapshot": token, "limit": 2, "offset": 0}),
        200,
    ).json()
    assert page0.get("has_more") is True
    page2 = assert_status(
        world.ada.get("/statement", params={"snapshot": token, "limit": 2, "offset": 2}),
        200,
    ).json()
    assert page2.get("has_more") is False
    past = assert_status(
        world.ada.get("/statement", params={"snapshot": token, "limit": 10, "offset": 99}),
        200,
    ).json()
    assert past["entries"] == []
    assert past.get("has_more") is False
    assert_error(world.ada.get("/statement", params={"snapshot": "bogus-token"}), 404, "not_found")
    assert_error(world.bob.get("/statement", params={"snapshot": token}), 404, "not_found")
    ignored = assert_status(
        world.ada.get("/statement", params={"snapshot": token, "foo": "bar"}),
        200,
    ).json()
    assert ignored["entries"] == page0["entries"]


def test_s3_c23_concurrent_corrections_same_expected_revision(reset, world):
    fx_body = fx.fixture(
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 500,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ]
    )
    reset(fx_body)
    body = {
        "expected_revision": 1,
        "amount": 480,
        "effective_at": "2026-09-20T12:00:00+00:00",
        "reason": "race",
    }

    def attempt():
        return world.ada.post(
            f"/payments/pay1/corrections",
            json=body,
            idempotency_key=new_key(),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        r1, r2 = [f.result() for f in (pool.submit(attempt), pool.submit(attempt))]
    assert sum(r.status_code == 201 for r in (r1, r2)) <= 1
    if any(r.status_code == 201 for r in (r1, r2)):
        assert any(r.status_code == 409 and error_code_safe(r) == "stale_revision" for r in (r1, r2))


def error_code_safe(resp: httpx.Response) -> str | None:
    try:
        return resp.json()["error"]["code"]
    except Exception:
        return None


def test_s3_c24_export_import_roundtrip(reset, api, base_url):
    fx_body = fx.fixture()
    reset(fx_body)
    ada = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    assert_status(
        ada.post("/payments", json={"to_handle": "bob", "amount": 33}, idempotency_key=new_key()),
        201,
    )
    export = assert_status(httpx.get(f"{base_url}/_test/export"), 200).json()
    reset(fx.fixture(users=[fx.user("solo", 1000)]))
    assert_status(httpx.post(f"{base_url}/_test/import", json=export), 204)
    ada2 = api().authenticate(fx.ADA["email"], fx.ADA["password"])
    me = assert_status(ada2.get("/me"), 200).json()
    assert me["handle"] == "ada"


def test_s3_c17_historical_overdraft_precedence(reset, world, me_wallet):
    fx_body = fx.fixture(
        users=[
            {**fx.ADA, "balance": 100},
            {**fx.BOB, "balance": 100},
            fx.CY,
        ],
        payments=[
            {
                "id": "pay1",
                "from_user_id": fx.ADA["id"],
                "to_user_id": fx.BOB["id"],
                "amount": 90,
                "visibility": "private",
                "created_at": "2026-09-20T12:00:00+00:00",
            }
        ],
    )
    reset(fx_body)
    assert_error(
        world.ada.post(
            "/payments/pay1/corrections",
            json={
                "expected_revision": 1,
                "amount": 200,
                "effective_at": "2026-09-19T00:00:00+00:00",
                "reason": "backdated overdraft",
            },
            idempotency_key=new_key(),
        ),
        409,
        "historical_overdraft",
    )


def test_s3_c27_closed_at_set_after_void(reset, world, authorize):
    fx_body = fx.fixture()
    reset(fx_body)
    auth = assert_status(authorize(amount=120), 201).json()
    aid = auth["authorization_id"]
    assert_status(world.ada.post(f"/authorizations/{aid}/void"), 200)
    listed = assert_status(world.ada.get("/authorizations"), 200).json()["authorizations"]
    row = next(a for a in listed if a["authorization_id"] == aid)
    assert row.get("closed_at")
