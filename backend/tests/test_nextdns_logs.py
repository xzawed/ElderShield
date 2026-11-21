"""NextDNS incident axis-C log pull — env-unset must never fail."""

from datetime import datetime, timezone

import httpx

from app.services.nextdns_logs import enrich_incident_dns, fetch_blocked_domains

FROM = datetime(2026, 11, 20, 3, 0, tzinfo=timezone.utc)
TO = datetime(2026, 11, 21, 4, 0, tzinfo=timezone.utc)

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}
DEVICE_UUID = "dev-nextdns-logs"


def test_fetch_blocked_domains_unset_env_returns_empty(monkeypatch) -> None:
    monkeypatch.delenv("NEXTDNS_API_KEY", raising=False)
    monkeypatch.delenv("NEXTDNS_PROFILE_ID", raising=False)
    assert fetch_blocked_domains(FROM, TO) == []


def test_fetch_blocked_domains_partial_env_returns_empty(monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.delenv("NEXTDNS_PROFILE_ID", raising=False)
    assert fetch_blocked_domains(FROM, TO) == []


def test_fetch_blocked_domains_httpx_mock(monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.setenv("NEXTDNS_PROFILE_ID", "abc123")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/profiles/abc123/logs"
        assert request.url.params.get("status") == "blocked"
        assert "from" in request.url.params
        assert "to" in request.url.params
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "timestamp": "2026-11-21T02:00:10.338Z",
                        "domain": "baidu.com",
                        "status": "blocked",
                    },
                    {
                        "timestamp": "2026-11-21T02:01:00.000Z",
                        "domain": "allowed.example",
                        "status": "default",
                    },
                ],
                "meta": {"pagination": {"cursor": None}},
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://api.nextdns.io") as client:
        events = fetch_blocked_domains(FROM, TO, client=client)
    assert events == [
        {"at": "2026-11-21T02:00:10.338Z", "domain": "baidu.com", "action": "block"},
    ]


def test_fetch_blocked_domains_api_failure_returns_empty(monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.setenv("NEXTDNS_PROFILE_ID", "abc123")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport, base_url="https://api.nextdns.io") as client:
        assert fetch_blocked_domains(FROM, TO, client=client) == []


def test_enrich_leaves_available_false_when_env_unset(monkeypatch) -> None:
    monkeypatch.delenv("NEXTDNS_API_KEY", raising=False)
    monkeypatch.delenv("NEXTDNS_PROFILE_ID", raising=False)
    payload = {
        "window": {"from": "2026-11-20T03:00:00Z", "to": "2026-11-21T04:00:00Z"},
        "dns": {"available": False, "unavailableReason": "nextdns_unset", "events": []},
    }
    out = enrich_incident_dns(payload)
    assert out["dns"]["available"] is False
    assert out["dns"]["events"] == []


def test_enrich_merges_events_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.setenv("NEXTDNS_PROFILE_ID", "abc123")
    monkeypatch.setattr(
        "app.services.nextdns_logs.fetch_blocked_domains",
        lambda *a, **k: [
            {"at": "2026-11-21T02:00:00Z", "domain": "baidu.com", "action": "block"},
        ],
    )
    payload = {
        "window": {"from": "2026-11-20T03:00:00Z", "to": "2026-11-21T04:00:00Z"},
        "dns": {"available": False, "unavailableReason": "client_pending", "events": []},
    }
    out = enrich_incident_dns(payload)
    assert out["dns"]["available"] is True
    assert out["dns"]["events"] == [
        {"at": "2026-11-21T02:00:00Z", "domain": "baidu.com", "action": "block"},
    ]
    assert payload["dns"]["available"] is False


def _heartbeat(client) -> None:
    r = client.post(
        "/api/v1/devices/heartbeat",
        headers=DEVICE,
        json={
            "deviceUuid": DEVICE_UUID,
            "appVersion": "1.0.0",
            "dnsConfigured": True,
            "callScreeningEnabled": True,
            "lastRuleVersion": 1,
        },
    )
    assert r.status_code == 200


def test_post_incident_succeeds_when_nextdns_unset(client, monkeypatch) -> None:
    monkeypatch.delenv("NEXTDNS_API_KEY", raising=False)
    monkeypatch.delenv("NEXTDNS_PROFILE_ID", raising=False)
    _heartbeat(client)
    body = {
        "incidentId": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "deviceUuid": DEVICE_UUID,
        "triggeredAt": "2026-11-21T03:00:00Z",
        "triggers": ["call_reject"],
        "window": {"from": "2026-11-20T03:00:00Z", "to": "2026-11-21T04:00:00Z"},
        "apps": [],
        "calls": [],
        "dns": {"available": False, "events": []},
    }
    r = client.post("/api/v1/devices/incidents", json=body, headers=DEVICE)
    assert r.status_code == 201
    assert r.json()["incidentId"] == body["incidentId"]


def test_export_enriches_dns_when_env_set(client, monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.setenv("NEXTDNS_PROFILE_ID", "abc123")
    monkeypatch.setattr(
        "app.services.nextdns_logs.fetch_blocked_domains",
        lambda *a, **k: [
            {"at": "2026-11-21T02:00:00Z", "domain": "baidu.com", "action": "block"},
        ],
    )
    _heartbeat(client)
    body = {
        "incidentId": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        "deviceUuid": DEVICE_UUID,
        "triggeredAt": "2026-11-21T03:00:00Z",
        "triggers": ["call_reject"],
        "window": {"from": "2026-11-20T03:00:00Z", "to": "2026-11-21T04:00:00Z"},
        "apps": [],
        "calls": [{"at": "2026-11-21T02:59:00Z", "countryIso": "CN", "decision": "Reject", "phoneHash": "h"}],
        "dns": {"available": False, "unavailableReason": "client_pending", "events": []},
    }
    posted = client.post("/api/v1/devices/incidents", json=body, headers=DEVICE)
    assert posted.status_code == 201
    incident_id = posted.json()["incidentId"]

    exp = client.get(f"/api/v1/admin/incidents/{incident_id}/export", headers=ADMIN)
    assert exp.status_code == 200
    payload = exp.json()["payload"]
    assert payload["dns"]["available"] is True
    assert payload["dns"]["events"] == [
        {"at": "2026-11-21T02:00:00Z", "domain": "baidu.com", "action": "block"},
    ]
    assert "phoneNumber" not in exp.text
