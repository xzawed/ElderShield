"""Admin UI cookie must be a session token, not the raw API key."""

from fastapi.testclient import TestClient

from app.web.auth import COOKIE_NAME, session_token_for


def test_login_sets_hmac_session_cookie_not_raw_key(client: TestClient) -> None:
    login = client.post(
        "/admin/ui/login",
        data={"api_key": "test-admin-key"},
        follow_redirects=False,
    )
    assert login.status_code in (303, 302)
    cookie = login.cookies.get(COOKIE_NAME)
    assert cookie is not None
    assert cookie != "test-admin-key"
    assert cookie == session_token_for("test-admin-key")


def test_raw_api_key_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(COOKIE_NAME, "test-admin-key")
    r = client.get("/admin/ui/restrictions/new", follow_redirects=False)
    assert r.status_code in (303, 302)
    assert "/admin/ui/login" in r.headers.get("location", "")
