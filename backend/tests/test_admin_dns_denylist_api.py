def test_admin_dns_denylist_from_restriction(client):
    create = client.post(
        "/api/v1/admin/country-restrictions",
        headers={"X-API-Key": "test-admin-key"},
        json={
            "name": "CN dns",
            "countries": ["CN"],
            "applyTo": ["dns", "call"],
            "enabled": True,
        },
    )
    assert create.status_code == 201

    r = client.get(
        "/api/v1/admin/dns-denylist",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "CN" in body["countries"]
    assert "cn" in body["tlds"]
    assert "*.cn" not in body["domains"]
    assert "baidu.com" in body["domains"]
    assert body["count"] == len(body["domains"]) + len(body["tlds"])

    denied = client.get(
        "/api/v1/admin/dns-denylist",
        headers={"X-API-Key": "test-device-key"},
    )
    assert denied.status_code in (401, 403)

    sync = client.post(
        "/api/v1/admin/dns-denylist/sync-nextdns",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert sync.status_code == 503
