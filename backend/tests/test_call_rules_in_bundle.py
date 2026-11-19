"""CallRules (whitelist) must ship in RuleBundle for device screening."""

ADMIN = {"X-API-Key": "test-admin-key"}
DEVICE = {"X-API-Key": "test-device-key"}


def test_call_rule_appears_in_rules_latest(client) -> None:
    created = client.post(
        "/api/v1/admin/call-rules",
        headers=ADMIN,
        json={
            "countryCodes": ["+86"],
            "whitelist": ["+8613812345678"],
            "enabled": True,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["whitelist"] == ["+8613812345678"]
    assert body["version"] == 1

    latest = client.get("/api/v1/rules/latest", headers=DEVICE).json()
    assert latest["version"] >= 1
    assert len(latest["callRules"]) == 1
    assert latest["callRules"][0]["whitelist"] == ["+8613812345678"]
    assert latest["callRules"][0]["enabled"] is True


def test_call_rule_create_bumps_bundle_version(client) -> None:
    before = client.get("/api/v1/rules/latest", headers=DEVICE).json()["version"]
    client.post(
        "/api/v1/admin/call-rules",
        headers=ADMIN,
        json={"countryCodes": ["+7"], "whitelist": ["+79161234567"], "enabled": True},
    )
    after = client.get("/api/v1/rules/latest", headers=DEVICE).json()["version"]
    assert after > before


def test_call_rule_requires_admin_key(client) -> None:
    assert (
        client.post(
            "/api/v1/admin/call-rules",
            headers=DEVICE,
            json={"whitelist": ["+821011112222"], "enabled": True},
        ).status_code
        == 403
    )
