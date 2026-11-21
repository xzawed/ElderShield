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


def test_root_redirects_to_admin_home(client) -> None:
    from app.web.spa import spa_home_path

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == spa_home_path()


def test_admin_shortcuts_redirect_to_spa_home(client) -> None:
    from app.web.spa import spa_index_available

    for path in ("/admin", "/admin/ui"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 302
        if spa_index_available():
            assert response.headers["location"] == "/admin/ui/"
        else:
            assert response.headers["location"] == "/admin/ui/login"
