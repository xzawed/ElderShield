def test_health_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "devices" in body
    assert "degradedDevices" in body
    assert "bundleVersion" in body
    assert "lastSeenAt" in body
    assert "syncLagSeconds" in body
