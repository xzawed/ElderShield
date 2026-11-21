"""Incident evidence pack — device POST + admin GET/export."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}

DEVICE_UUID = "dev-incident-api"


def _heartbeat(client, device_uuid: str = DEVICE_UUID) -> None:
    payload = {
        "deviceUuid": device_uuid,
        "appVersion": "1.0.0",
        "dnsConfigured": True,
        "callScreeningEnabled": True,
        "lastRuleVersion": 1,
    }
    r = client.post("/api/v1/devices/heartbeat", headers=DEVICE, json=payload)
    assert r.status_code == 200


def _incident_body(**overrides):
    body = {
        "incidentId": "11111111-1111-1111-1111-111111111111",
        "deviceUuid": DEVICE_UUID,
        "triggeredAt": "2026-11-21T03:00:00Z",
        "triggers": ["call_reject"],
        "apps": [],
        "calls": [],
        "dns": {"available": False, "events": []},
    }
    body.update(overrides)
    return body


def test_post_incident_rejects_raw_phone(client) -> None:
    _heartbeat(client)
    body = _incident_body(
        calls=[
            {
                "at": "2026-11-21T02:59:00Z",
                "countryIso": "CN",
                "decision": "Reject",
                "phoneNumber": "+86139",
            }
        ],
    )
    r = client.post("/api/v1/devices/incidents", json=body, headers=DEVICE)
    assert r.status_code in (400, 422)


def test_post_incident_phone_hash_only_no_raw_phone(client) -> None:
    _heartbeat(client)
    body = _incident_body(
        calls=[
            {
                "at": "2026-11-21T02:59:00Z",
                "countryIso": "CN",
                "decision": "Reject",
                "phoneHash": "abc123hash",
            }
        ],
    )
    r = client.post("/api/v1/devices/incidents", json=body, headers=DEVICE)
    assert r.status_code == 201
    incident_id = r.json()["incidentId"]

    listed = client.get(f"/api/v1/admin/devices/{DEVICE_UUID}/incidents", headers=ADMIN)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    blob = str(items[0])
    assert "phoneHash" in blob
    assert "phoneNumber" not in blob
    assert "abc123hash" in blob

    got = client.get(f"/api/v1/admin/incidents/{incident_id}", headers=ADMIN)
    assert got.status_code == 200
    detail = str(got.json())
    assert "phoneHash" in detail
    assert "phoneNumber" not in detail


def test_post_incident_merge_within_one_hour(client) -> None:
    _heartbeat(client)
    first = _incident_body(
        incidentId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        triggeredAt="2026-11-21T03:00:00Z",
        triggers=["call_reject"],
        calls=[
            {
                "at": "2026-11-21T02:59:00Z",
                "countryIso": "CN",
                "decision": "Reject",
                "phoneHash": "hash-a",
            }
        ],
    )
    second = _incident_body(
        incidentId="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        triggeredAt="2026-11-21T03:30:00Z",
        triggers=["app_scan"],
        calls=[
            {
                "at": "2026-11-21T03:10:00Z",
                "countryIso": "CN",
                "decision": "Reject",
                "phoneHash": "hash-b",
            }
        ],
        apps=[{"packageName": "com.fake.risk"}],
    )
    r1 = client.post("/api/v1/devices/incidents", json=first, headers=DEVICE)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/devices/incidents", json=second, headers=DEVICE)
    assert r2.status_code == 200

    listed = client.get(f"/api/v1/admin/devices/{DEVICE_UUID}/incidents", headers=ADMIN)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert set(items[0]["triggers"]) == {"call_reject", "app_scan"}


def test_export_incident_has_no_raw_phone(client) -> None:
    _heartbeat(client)
    body = _incident_body(
        incidentId="cccccccc-cccc-cccc-cccc-cccccccccccc",
        calls=[
            {
                "at": "2026-11-21T02:59:00Z",
                "countryIso": "CN",
                "decision": "Reject",
                "phoneHash": "export-hash",
            }
        ],
    )
    r = client.post("/api/v1/devices/incidents", json=body, headers=DEVICE)
    assert r.status_code == 201
    incident_id = r.json()["incidentId"]

    exp = client.get(f"/api/v1/admin/incidents/{incident_id}/export", headers=ADMIN)
    assert exp.status_code == 200
    assert "phoneNumber" not in exp.text
    assert "export-hash" in exp.text
    cd = exp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert f"incident-{incident_id}.json" in cd
