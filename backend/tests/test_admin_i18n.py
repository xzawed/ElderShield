from fastapi.testclient import TestClient


def test_lang_cookie_switches_nav_copy(client: TestClient) -> None:
    login = client.post(
        "/admin/ui/login",
        data={"api_key": "test-admin-key"},
        follow_redirects=False,
    )
    assert login.status_code in (303, 302)

    en = client.get("/admin/ui/lang?set=en&next=/admin/ui/restrictions", follow_redirects=False)
    assert en.status_code in (303, 302)
    assert "es_admin_lang=en" in en.headers.get("set-cookie", "")

    page_en = client.get("/admin/ui/restrictions")
    assert page_en.status_code == 200
    assert "Country restrictions" in page_en.text

    ko = client.get("/admin/ui/lang?set=ko&next=/admin/ui/restrictions", follow_redirects=False)
    assert ko.status_code in (303, 302)
    page_ko = client.get("/admin/ui/restrictions")
    assert page_ko.status_code == 200
    assert "국가 제한" in page_ko.text


def test_countries_api_includes_bilingual_names(client: TestClient) -> None:
    r = client.get("/api/v1/admin/countries", headers={"X-API-Key": "test-admin-key"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 140
    kr = next(c for c in body if c["code"] == "KR")
    assert kr["nameEn"]
    assert kr["nameKo"]
    assert kr["name"] == kr["nameEn"]
    assert "callingCode" in kr


def test_restriction_form_lists_many_countries(client: TestClient) -> None:
    client.post("/admin/ui/login", data={"api_key": "test-admin-key"})
    client.get("/admin/ui/lang?set=ko&next=/admin/ui/restrictions/new")
    page = client.get("/admin/ui/restrictions/new")
    assert page.status_code == 200
    assert 'value="CN"' in page.text
    assert 'value="US"' in page.text
    assert "country_filter" in page.text
    # Korean label for China when lang=ko
    assert "중국" in page.text
