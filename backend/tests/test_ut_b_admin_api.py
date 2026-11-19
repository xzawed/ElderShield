"""UT-B-10..16 — Admin country-restrictions API."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def test_ut_b_10_post_creates_multi_countries(client) -> None:
    r = client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={
            "name": "고위험",
            "countries": ["CN", "RU", "KP"],
            "applyTo": ["call", "dns"],
            "enabled": True,
            "description": "t",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["countries"] == ["CN", "RU", "KP"]
    assert body["version"] == 1


def test_ut_b_11_get_list_includes_created(client) -> None:
    client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={"name": "A", "countries": ["CN"], "applyTo": ["call"], "enabled": True},
    )
    r = client.get("/api/v1/admin/country-restrictions", headers=ADMIN)
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_ut_b_12_put_updates_and_bumps_version(client) -> None:
    created = client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={"name": "A", "countries": ["CN"], "applyTo": ["call"], "enabled": True},
    ).json()
    r = client.put(
        f"/api/v1/admin/country-restrictions/{created['id']}",
        headers=ADMIN,
        json={"countries": ["CN", "RU"]},
    )
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert r.json()["countries"] == ["CN", "RU"]


def test_ut_b_13_delete_removes(client) -> None:
    created = client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={"name": "A", "countries": ["CN"], "applyTo": ["call"], "enabled": True},
    ).json()
    d = client.delete(f"/api/v1/admin/country-restrictions/{created['id']}", headers=ADMIN)
    assert d.status_code == 204
    listed = client.get("/api/v1/admin/country-restrictions", headers=ADMIN).json()
    assert all(item["id"] != created["id"] for item in listed)


def test_ut_b_14_countries_master(client) -> None:
    r = client.get("/api/v1/admin/countries", headers=ADMIN)
    assert r.status_code == 200
    codes = {c["code"] for c in r.json()}
    assert {"CN", "RU", "KP"}.issubset(codes)
    cn = next(c for c in r.json() if c["code"] == "CN")
    assert cn["callingCode"] == "+86"


def test_ut_b_15_missing_or_bad_admin_key(client) -> None:
    assert client.get("/api/v1/admin/countries").status_code in (401, 403)
    assert (
        client.get("/api/v1/admin/countries", headers={"X-API-Key": "wrong"}).status_code
        in (401, 403)
    )


def test_ut_b_16_device_key_forbidden_on_admin(client) -> None:
    r = client.get("/api/v1/admin/countries", headers=DEVICE)
    assert r.status_code == 403


def test_ut_b_04_http_rejects_countries_string(client) -> None:
    r = client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={
            "name": "bad",
            "countries": "CN",
            "applyTo": ["call"],
            "enabled": True,
        },
    )
    assert r.status_code == 422


def test_ut_b_05_http_rejects_empty_countries_when_enabled(client) -> None:
    r = client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={
            "name": "empty",
            "countries": [],
            "applyTo": ["call"],
            "enabled": True,
        },
    )
    assert r.status_code == 422
