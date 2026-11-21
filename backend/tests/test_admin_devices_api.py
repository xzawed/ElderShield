"""GET /admin/devices — registered device list + status."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def test_admin_devices_lists_heartbeat_devices(client) -> None:
    client.post(
        "/api/v1/devices/heartbeat",
        headers=DEVICE,
        json={
            "deviceUuid": "dev-admin-list-1",
            "appVersion": "1.0.0",
            "dnsConfigured": True,
            "callScreeningEnabled": True,
            "lastRuleVersion": 3,
        },
    )
    r = client.get("/api/v1/admin/devices", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    match = next(d for d in body if d["deviceUuid"] == "dev-admin-list-1")
    assert match["appVersion"] == "1.0.0"
    assert match["dnsConfigured"] is True
    assert match["callScreeningEnabled"] is True
    assert match["lastRuleVersion"] == 3
    assert match["lastSyncAt"]


def test_admin_devices_requires_admin_key(client) -> None:
    assert client.get("/api/v1/admin/devices").status_code == 401
    assert client.get("/api/v1/admin/devices", headers=DEVICE).status_code == 403


def test_admin_device_detail_includes_token_status(client) -> None:
    client.post(
        "/api/v1/devices/heartbeat",
        headers=DEVICE,
        json={
            "deviceUuid": "dev-token-status-1",
            "appVersion": "1.0.0",
            "dnsConfigured": False,
            "callScreeningEnabled": True,
            "lastRuleVersion": 1,
        },
    )
    r = client.get("/api/v1/admin/devices/dev-token-status-1", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert "device" in body
    assert body["tokenStatus"] in ("active", "revoked", "none")
    # Heartbeat-only device uses shared fleet key → no bound token hash.
    assert body["tokenStatus"] == "none"
