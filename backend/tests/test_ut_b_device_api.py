"""UT-B-20..25 — Device rules / heartbeat / scan-result API."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def _create_restriction(client, countries=None):
    return client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={
            "name": "고위험",
            "countries": countries or ["CN", "RU"],
            "applyTo": ["call", "dns"],
            "enabled": True,
        },
    ).json()


def test_ut_b_20_rules_latest_returns_bundle(client) -> None:
    _create_restriction(client)
    r = client.get("/api/v1/rules/latest", headers=DEVICE)
    assert r.status_code == 200
    body = r.json()
    assert "version" in body
    assert isinstance(body["version"], int)
    assert "countryRestrictions" in body
    assert "updatedAt" in body


def test_ut_b_21_rules_latest_reflects_admin_change(client) -> None:
    created = _create_restriction(client, ["CN"])
    before = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    client.put(
        f"/api/v1/admin/country-restrictions/{created['id']}",
        headers=ADMIN,
        json={"countries": ["CN", "RU"]},
    )
    after = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert after["version"] > before["version"]
    codes = after["countryRestrictions"][0]["countries"]
    assert codes == ["CN", "RU"]


def test_ut_b_22_heartbeat_updates_device(client) -> None:
    payload = {
        "deviceUuid": "dev-ut-b-22",
        "appVersion": "1.0.0",
        "dnsConfigured": True,
        "callScreeningEnabled": True,
        "lastRuleVersion": 1,
    }
    r = client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["deviceUuid"] == "dev-ut-b-22"
    assert body["lastSyncAt"]


def test_ut_b_23_scan_result_persisted(client) -> None:
    payload = {
        "deviceUuid": "dev-ut-b-23",
        "suspiciousApps": [
            {
                "packageName": "com.fake.app",
                "installer": None,
                "dangerousPermissions": ["READ_SMS"],
                "riskScore": 85,
            }
        ],
    }
    r = client.post("/api/v1/devices/apps/scan-result", headers=DEVICE, json=payload)
    assert r.status_code == 200
    listed = client.get(
        "/api/v1/admin/devices/dev-ut-b-23/scan-results",
        headers=ADMIN,
    )
    assert listed.status_code == 200
    apps = listed.json()
    assert any(a["packageName"] == "com.fake.app" for a in apps)


def test_ut_b_24_device_key_missing(client) -> None:
    assert client.get("/api/v1/rules/latest").status_code == 401


def test_ut_b_25_admin_key_forbidden_on_device_routes(client) -> None:
    assert client.get("/api/v1/rules/latest", headers=ADMIN).status_code == 403
    assert (
        client.post(
            "/api/v1/devices/heartbeat",
            headers=ADMIN,
            json={
                "deviceUuid": "x",
                "appVersion": "1.0.0",
                "dnsConfigured": False,
                "callScreeningEnabled": False,
                "lastRuleVersion": 0,
            },
        ).status_code
        == 403
    )
