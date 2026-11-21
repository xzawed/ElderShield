from app.web.auth import (
    ADMIN_UI_REQUEST_HEADER,
    ADMIN_UI_REQUEST_HEADER_VALUE,
    COOKIE_NAME,
    clear_admin_session_cookie,
)


def _spa_headers() -> dict[str, str]:
    return {ADMIN_UI_REQUEST_HEADER: ADMIN_UI_REQUEST_HEADER_VALUE}


def test_json_login_sets_session_cookie(client) -> None:
    r = client.post("/admin/ui/api/login", json={"apiKey": "test-admin-key"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert COOKIE_NAME in r.cookies


def test_json_login_bad_key_401(client) -> None:
    r = client.post("/admin/ui/api/login", json={"apiKey": "wrong-key"})
    assert r.status_code == 401
    assert r.json() == {"ok": False, "error": "invalid"}
    assert COOKIE_NAME not in r.cookies


def test_admin_api_accepts_session_cookie_with_csrf_header(client) -> None:
    login = client.post("/admin/ui/api/login", json={"apiKey": "test-admin-key"})
    assert login.status_code == 200
    client.cookies.set(COOKIE_NAME, login.cookies[COOKIE_NAME])

    r = client.get("/api/v1/admin/devices", headers=_spa_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_api_rejects_cookie_without_csrf_header(client) -> None:
    login = client.post("/admin/ui/api/login", json={"apiKey": "test-admin-key"})
    assert login.status_code == 200
    client.cookies.set(COOKIE_NAME, login.cookies[COOKIE_NAME])

    r = client.get("/api/v1/admin/devices")
    assert r.status_code == 401
    assert r.json()["detail"] == "Missing admin UI request header"


def test_device_api_key_header_forbidden_even_with_admin_cookie(client) -> None:
    login = client.post("/admin/ui/api/login", json={"apiKey": "test-admin-key"})
    client.cookies.set(COOKIE_NAME, login.cookies[COOKIE_NAME])

    r = client.get(
        "/api/v1/admin/devices",
        headers={**_spa_headers(), "X-API-Key": "test-device-key"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Admin key required"


def test_logout_clears_cookie_without_prior_auth(client, monkeypatch) -> None:
    monkeypatch.setenv("COOKIE_SECURE", "1")
    login = client.post("/admin/ui/api/login", json={"apiKey": "test-admin-key"})
    assert login.status_code == 200
    client.cookies.set(COOKIE_NAME, login.cookies[COOKIE_NAME])

    r = client.get("/admin/ui/logout", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/admin/ui/login" in r.headers.get("location", "")
    # Starlette TestClient exposes Set-Cookie; deleted cookie has max-age=0 or empty value.
    set_cookie = r.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "max-age=0" in set_cookie.lower() or f"{COOKIE_NAME}=" in set_cookie


def test_clear_admin_session_cookie_matches_secure_flag(monkeypatch) -> None:
    from fastapi.responses import Response

    monkeypatch.setenv("COOKIE_SECURE", "1")
    resp = Response()
    clear_admin_session_cookie(resp)
    raw = resp.headers.get("set-cookie", "")
    assert COOKIE_NAME in raw
    assert "secure" in raw.lower()
    assert "samesite=lax" in raw.lower()
