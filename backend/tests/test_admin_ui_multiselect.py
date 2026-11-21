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
    # Checkbox multi-select (not native <select multiple>)
    assert 'name="countries"' in html and 'type="checkbox"' in html
    assert 'name="apply_to"' in html
    assert 'id="country_filter"' in html
    assert 'id="country_chips"' in html
    for code in ("CN", "RU", "KP"):
        assert f'value="{code}"' in html
        assert f'value="{code}"' in html and "checked" in html
    # At least the three countries + call + dns checked
    assert html.count("checked") >= 5


def test_admin_ui_login_required(client: TestClient) -> None:
    # List GET is SPA shell; Jinja form routes still enforce server-side login.
    r = client.get("/admin/ui/restrictions/new", follow_redirects=False)
    assert r.status_code in (303, 302)
    assert "/admin/ui/login" in r.headers.get("location", "")


def test_restriction_new_form_uses_checkbox_multiselect(client: TestClient) -> None:
    client.post("/admin/ui/login", data={"api_key": "test-admin-key"})
    page = client.get("/admin/ui/restrictions/new")
    assert page.status_code == 200
    html = page.text
    assert "<select" not in html
    assert 'name="countries"' in html
    assert "country-cb" in html
    assert 'name="apply_to"' in html
    assert "통화" in html or "Calls" in html
    assert "country_chips" in html
