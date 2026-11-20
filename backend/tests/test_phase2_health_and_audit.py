"""Phase 2C/A — health signals, role_lost, allowlist, audit."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def test_heartbeat_health_fields_and_degraded(client) -> None:
    payload = {
        "deviceUuid": "dev-p2-health",
        "appVersion": "0.2.0",
        "dnsConfigured": False,
        "callScreeningEnabled": True,
        "lastRuleVersion": 3,
        "dnsHostClass": "none",
        "lastSyncOk": False,
        "lastSyncErrorCode": "network",
        "cachedBundleVersion": 2,
    }
    assert client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=payload).status_code == 200
    detail = client.get("/api/v1/admin/devices/dev-p2-health", headers=ADMIN)
    assert detail.status_code == 200
    body = detail.json()
    d = body["device"]
    assert d["protectionDegraded"] is True
    assert d["dnsHostClass"] == "none"
    assert d["lastSyncOk"] is False
    assert d["cachedBundleVersion"] == 2


def test_role_lost_health_event_on_transition(client) -> None:
    base = {
        "deviceUuid": "dev-p2-role",
        "appVersion": "0.2.0",
        "dnsConfigured": True,
        "dnsHostClass": "nextdns",
        "lastRuleVersion": 1,
        "lastSyncOk": True,
        "cachedBundleVersion": 1,
    }
    on = {
        **base,
        "callScreeningEnabled": True,
        "callScreeningHeldBy": "com.eldershield",
        "callScreeningPeers": [],
    }
    off_no_peers = {
        **base,
        "callScreeningEnabled": False,
        "callScreeningHeldBy": None,
        "callScreeningPeers": [],
    }
    off_with_peers = {
        **base,
        "callScreeningEnabled": False,
        "callScreeningHeldBy": None,
        "callScreeningPeers": ["com.bitdefender.security"],
    }
    assert client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=on).status_code == 200
    assert client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=off_no_peers).status_code == 200
    detail = client.get("/api/v1/admin/devices/dev-p2-role", headers=ADMIN).json()
    assert "role_lost" not in [e["type"] for e in detail["healthEvents"]]

    # Re-enable then lose role while peers present (Bitdefender coexistence).
    assert client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=on).status_code == 200
    assert client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=off_with_peers).status_code == 200
    detail = client.get("/api/v1/admin/devices/dev-p2-role", headers=ADMIN).json()
    types = [e["type"] for e in detail["healthEvents"]]
    assert "role_lost" in types


def test_health_events_endpoint(client) -> None:
    r = client.post(
        "/api/v1/devices/health-events",
        headers=DEVICE,
        json={
            "deviceUuid": "dev-p2-drift",
            "events": [{"type": "dns_drift", "detail": "host_class=other"}],
        },
    )
    assert r.status_code == 200
    assert r.json()["saved"] == 1
    detail = client.get("/api/v1/admin/devices/dev-p2-drift", headers=ADMIN).json()
    assert detail["healthEvents"][0]["type"] == "dns_drift"


def test_scan_reasons_and_allowlist_audit(client) -> None:
    scan = client.post(
        "/api/v1/devices/apps/scan-result",
        headers=DEVICE,
        json={
            "deviceUuid": "dev-p2-scan",
            "suspiciousApps": [
                {
                    "packageName": "com.overlay.scam",
                    "installer": None,
                    "dangerousPermissions": [],
                    "riskScore": 85,
                    "reasons": ["overlay_permission", "installer_null"],
                }
            ],
        },
    )
    assert scan.status_code == 200
    scans = client.get(
        "/api/v1/admin/devices/dev-p2-scan/scan-results", headers=ADMIN
    ).json()
    assert scans[0]["reasons"] == ["overlay_permission", "installer_null"]

    al = client.post(
        "/api/v1/admin/app-allowlist",
        headers=ADMIN,
        json={"packageName": "com.overlay.scam", "note": "false positive"},
    )
    assert al.status_code == 201
    listed = client.get("/api/v1/admin/app-allowlist", headers=ADMIN).json()
    assert any(x["packageName"] == "com.overlay.scam" for x in listed)

    created = client.post(
        "/api/v1/admin/country-restrictions",
        headers=ADMIN,
        json={
            "name": "p2",
            "countries": ["CN"],
            "applyTo": ["dns"],
            "enabled": True,
        },
    )
    assert created.status_code == 201
    audit = client.get("/api/v1/admin/audit", headers=ADMIN).json()
    actions = {a["action"] for a in audit}
    assert "create" in actions
    assert "upsert" in actions
