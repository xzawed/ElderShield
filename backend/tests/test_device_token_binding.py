ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def _open_window(client):
    assert (
        client.post(
            "/api/v1/admin/enrollment-window",
            headers=ADMIN,
            json={"enabled": True, "ttlMinutes": 30},
        ).status_code
        == 200
    )


def _enroll(client, *, integrity="tok-a"):
    r = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": integrity, "appVersion": "0.2.0"},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_device_token_cannot_heartbeat_other_uuid(client):
    _open_window(client)
    a = _enroll(client, integrity="bind-a")
    b = _enroll(client, integrity="bind-b")

    # Token A must not update device B
    r = client.post(
        "/api/v1/devices/heartbeat",
        headers={"X-API-Key": a["deviceToken"]},
        json={
            "deviceUuid": b["deviceUuid"],
            "appVersion": "9.9.9",
            "dnsConfigured": True,
            "callScreeningEnabled": True,
            "lastRuleVersion": 99,
            "lastSyncOk": True,
        },
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "device_uuid_mismatch"

    # Own UUID still works
    ok = client.post(
        "/api/v1/devices/heartbeat",
        headers={"X-API-Key": a["deviceToken"]},
        json={
            "deviceUuid": a["deviceUuid"],
            "appVersion": "0.2.0",
            "dnsConfigured": False,
            "callScreeningEnabled": True,
            "lastRuleVersion": 1,
            "lastSyncOk": True,
        },
    )
    assert ok.status_code == 200


def test_device_token_cannot_poison_other_health_or_scan(client):
    _open_window(client)
    a = _enroll(client, integrity="poison-a")
    b = _enroll(client, integrity="poison-b")

    he = client.post(
        "/api/v1/devices/health-events",
        headers={"X-API-Key": a["deviceToken"]},
        json={"deviceUuid": b["deviceUuid"], "events": [{"type": "dns_drift", "detail": "x"}]},
    )
    assert he.status_code == 403

    sc = client.post(
        "/api/v1/devices/apps/scan-result",
        headers={"X-API-Key": a["deviceToken"]},
        json={
            "deviceUuid": b["deviceUuid"],
            "suspiciousApps": [
                {
                    "packageName": "com.evil",
                    "dangerousPermissions": [],
                    "riskScore": 90,
                    "reasons": ["x"],
                }
            ],
        },
    )
    assert sc.status_code == 403


def test_shared_device_key_still_allows_any_uuid(client):
    # Lab shared key remains fleet-wide for debug devices.
    r = client.post(
        "/api/v1/devices/heartbeat",
        headers=DEVICE,
        json={
            "deviceUuid": "lab-shared-uuid-001",
            "appVersion": "0.2.0",
            "dnsConfigured": False,
            "callScreeningEnabled": False,
            "lastRuleVersion": 0,
            "lastSyncOk": True,
        },
    )
    assert r.status_code == 200
