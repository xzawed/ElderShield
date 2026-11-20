ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def test_enroll_rejected_when_window_closed(client):
    r = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": "x", "appVersion": "0.2.0"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "enrollment_closed"


def test_enroll_then_heartbeat_with_device_token(client):
    open_r = client.post(
        "/api/v1/admin/enrollment-window",
        headers=ADMIN,
        json={"enabled": True, "ttlMinutes": 30},
    )
    assert open_r.status_code == 200
    assert open_r.json()["open"] is True

    enroll = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": "lab", "appVersion": "0.2.0", "model": "SM-S908N"},
    )
    assert enroll.status_code == 201
    body = enroll.json()
    assert body["deviceUuid"]
    assert len(body["deviceToken"]) >= 32

    token = body["deviceToken"]
    uuid = body["deviceUuid"]
    hb = client.post(
        "/api/v1/devices/heartbeat",
        headers={"X-API-Key": token},
        json={
            "deviceUuid": uuid,
            "appVersion": "0.2.0",
            "dnsConfigured": False,
            "callScreeningEnabled": True,
            "callScreeningHeldBy": "com.eldershield",
            "callScreeningPeers": [],
            "lastRuleVersion": 1,
            "lastSyncOk": True,
        },
    )
    assert hb.status_code == 200

    # shared lab key still works
    rules = client.get("/api/v1/rules/latest", headers=DEVICE)
    assert rules.status_code == 200


def test_revoked_device_token_rejected(client):
    client.post(
        "/api/v1/admin/enrollment-window",
        headers=ADMIN,
        json={"enabled": True, "ttlMinutes": 10},
    )
    enroll = client.post(
        "/api/v1/devices/enroll",
        json={"appVersion": "0.2.0"},
    ).json()
    token = enroll["deviceToken"]
    uuid = enroll["deviceUuid"]

    rev = client.delete(f"/api/v1/admin/devices/{uuid}/token", headers=ADMIN)
    assert rev.status_code == 204

    hb = client.post(
        "/api/v1/devices/heartbeat",
        headers={"X-API-Key": token},
        json={
            "deviceUuid": uuid,
            "appVersion": "0.2.0",
            "dnsConfigured": False,
            "callScreeningEnabled": False,
            "lastRuleVersion": 0,
        },
    )
    assert hb.status_code == 403


def test_close_enrollment_window(client):
    client.post(
        "/api/v1/admin/enrollment-window",
        headers=ADMIN,
        json={"enabled": True, "ttlMinutes": 5},
    )
    closed = client.post(
        "/api/v1/admin/enrollment-window",
        headers=ADMIN,
        json={"enabled": False},
    )
    assert closed.status_code == 200
    assert closed.json()["open"] is False
    assert (
        client.post("/api/v1/devices/enroll", json={"appVersion": "0.2.0"}).status_code == 403
    )


def test_integrity_fails_when_skip_disabled(client, monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.Settings(
            database_url="sqlite://",
            admin_api_key="test-admin-key",
            device_api_key="test-device-key",
            enroll_skip_integrity=False,
            play_integrity_enabled=False,
        ),
    )
    client.post(
        "/api/v1/admin/enrollment-window",
        headers=ADMIN,
        json={"enabled": True, "ttlMinutes": 5},
    )
    r = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": "anything", "appVersion": "0.2.0"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "integrity_failed"
