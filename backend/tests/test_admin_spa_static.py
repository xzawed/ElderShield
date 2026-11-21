"""Phase A — SPA static shell coexists with Jinja admin routes."""

import pytest
from fastapi.testclient import TestClient

from app.web.spa import SPA_ASSETS_DIR, SPA_INDEX

pytestmark = pytest.mark.skipif(
    not SPA_INDEX.is_file(),
    reason="admin SPA build missing (run npm run build in admin-web)",
)


def test_spa_home_serves_index_shell(client: TestClient) -> None:
    r = client.get("/admin/ui/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert 'id="root"' in r.text


def test_spa_login_path_serves_same_shell(client: TestClient) -> None:
    r = client.get("/admin/ui/login")
    assert r.status_code == 200
    assert 'id="root"' in r.text


def test_jinja_restrictions_still_served(client: TestClient) -> None:
    client.post(
        "/admin/ui/login",
        data={"api_key": "test-admin-key"},
        follow_redirects=True,
    )
    r = client.get("/admin/ui/restrictions")
    assert r.status_code == 200
    assert "restrictions" in r.text.lower()


def test_spa_asset_under_admin_ui_assets(client: TestClient) -> None:
    if not SPA_ASSETS_DIR.is_dir():
        pytest.skip("no SPA assets directory")
    assets = sorted(SPA_ASSETS_DIR.glob("*"))
    if not assets:
        pytest.skip("no built SPA assets")
    first = assets[0].name
    url = f"/admin/ui/assets/{first}"
    r = client.get(url)
    assert r.status_code == 200
    assert len(r.content) > 0


def test_bare_admin_ui_redirects_to_spa_home(client: TestClient) -> None:
    r = client.get("/admin/ui", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers.get("location") == "/admin/ui/"


def test_spa_assets_reject_path_traversal(client: TestClient) -> None:
    r = client.get("/admin/ui/assets/../../main.py")
    assert r.status_code in (404, 400, 403)


def test_spa_devices_shell_serves_index(client: TestClient) -> None:
    r = client.get("/admin/ui/devices")
    assert r.status_code == 200
    assert 'id="root"' in r.text
