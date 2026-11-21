"""Admin DNS logs thin proxy."""

import httpx

ADMIN = {"X-API-Key": "test-admin-key"}
FROM = "2026-11-21T00:00:00Z"
TO = "2026-11-21T12:00:00Z"


def test_dns_logs_unset_returns_503(client, monkeypatch) -> None:
    monkeypatch.delenv("NEXTDNS_API_KEY", raising=False)
    monkeypatch.delenv("NEXTDNS_PROFILE_ID", raising=False)
    r = client.get(f"/api/v1/admin/dns-logs?from={FROM}&to={TO}", headers=ADMIN)
    assert r.status_code == 503
    assert r.json() == {"error": "nextdns_unset"}


def test_dns_logs_happy_path_mock(client, monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.setenv("NEXTDNS_PROFILE_ID", "prof1")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/profiles/prof1/logs" in str(request.url)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "timestamp": "2026-11-21T02:00:00Z",
                        "domain": "evil.example",
                        "status": "blocked",
                    }
                ],
                "meta": {"pagination": {}},
            },
        )

    transport = httpx.MockTransport(handler)
    real_client_cls = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs = dict(kwargs)
        kwargs["transport"] = transport
        kwargs.setdefault("base_url", "https://api.nextdns.io")
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr("app.services.nextdns_logs.httpx.Client", client_factory)

    r = client.get(
        f"/api/v1/admin/dns-logs?from={FROM}&to={TO}&status=blocked&limit=50",
        headers=ADMIN,
    )
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert body["events"][0]["domain"] == "evil.example"
    assert body["events"][0]["status"] == "blocked"


def test_dns_logs_requires_admin(client, monkeypatch) -> None:
    monkeypatch.setenv("NEXTDNS_API_KEY", "k")
    monkeypatch.setenv("NEXTDNS_PROFILE_ID", "prof1")
    r = client.get(f"/api/v1/admin/dns-logs?from={FROM}&to={TO}")
    assert r.status_code == 401
