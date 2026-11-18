"""S2.2 — admin UI multi-select countries persist on create/reopen."""

from fastapi.testclient import TestClient


def test_admin_ui_create_and_reopen_keeps_multi_countries(client: TestClient) -> None:
    login = client.post(
        "/admin/ui/login",
        data={"api_key": "test-admin-key"},
        follow_redirects=False,
    )
    assert login.status_code in (303, 302)

    create = client.post(
        "/admin/ui/restrictions",
        data={
            "name": "고위험",
            "countries": ["CN", "RU", "KP"],
            "apply_to": ["call", "dns"],
            "enabled": "on",
            "description": "ui-test",
        },
        follow_redirects=False,
    )
    assert create.status_code in (303, 302)
    location = create.headers.get("location", "")
    assert "/admin/ui/restrictions/" in location

    edit = client.get(location)
    assert edit.status_code == 200
    html = edit.text
    # selected options must survive reopen
    assert 'value="CN"' in html and "selected" in html
    assert "CN" in html and "RU" in html and "KP" in html
    assert html.count('selected') >= 3


def test_admin_ui_login_required(client: TestClient) -> None:
    r = client.get("/admin/ui/restrictions", follow_redirects=False)
    assert r.status_code in (303, 302)
    assert "/admin/ui/login" in r.headers.get("location", "")
