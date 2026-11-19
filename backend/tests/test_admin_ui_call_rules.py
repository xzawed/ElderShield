"""Admin UI — create CallRule whitelist and see it on the page."""

from fastapi.testclient import TestClient


def _login(client: TestClient) -> None:
    client.post(
        "/admin/ui/login",
        data={"api_key": "test-admin-key"},
        follow_redirects=False,
    )


def test_admin_ui_create_call_rule_shows_whitelist(client: TestClient) -> None:
    _login(client)
    create = client.post(
        "/admin/ui/call-rules",
        data={
            "whitelist": "+8613812345678\n+821011112222",
            "country_codes": "+86",
            "enabled": "on",
        },
        follow_redirects=False,
    )
    assert create.status_code in (303, 302)
    assert create.headers.get("location", "").endswith("/admin/ui/call-rules")

    page = client.get("/admin/ui/call-rules")
    assert page.status_code == 200
    assert "+8613812345678" in page.text
    assert "+821011112222" in page.text

    latest = client.get(
        "/api/v1/rules/latest",
        headers={"X-API-Key": "test-device-key"},
    )
    assert latest.status_code == 200
    body = latest.json()
    assert body["version"] >= 1
    assert any("+8613812345678" in r.get("whitelist", []) for r in body["callRules"])
