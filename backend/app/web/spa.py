"""Serve built React admin SPA alongside Jinja admin routes."""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

SPA_DIR = Path(__file__).resolve().parents[1] / "static" / "admin-spa"
SPA_INDEX = SPA_DIR / "index.html"
SPA_ASSETS_DIR = SPA_DIR / "assets"

# Exact first segments after /admin/ui/ owned by the SPA shell (not Jinja list pages).
SPA_SHELL_SEGMENTS = frozenset(
    {
        "login",
        "devices",
        "audit",
        "dns-logs",
        "incidents",
        "restrictions",
        "call-rules",
        "dns-denylist",
        "allowlist",
    }
)

# Parameterized SPA shells (shadow Jinja device detail when SPA is built).
SPA_PARAM_PATHS = (
    "/admin/ui/incidents/{incident_id}",
    "/admin/ui/devices/{device_uuid}",
)


def spa_index_available() -> bool:
    return SPA_INDEX.is_file()


def spa_home_path() -> str:
    return "/admin/ui/" if spa_index_available() else "/admin/ui/login"


def serve_spa_index() -> FileResponse:
    return FileResponse(SPA_INDEX, media_type="text/html")


def register_admin_spa(app: FastAPI) -> None:
    """Register SPA asset mount and shell routes before the Jinja admin UI router."""
    if SPA_ASSETS_DIR.is_dir():
        app.mount(
            "/admin/ui/assets",
            StaticFiles(directory=str(SPA_ASSETS_DIR)),
            name="admin-spa-assets",
        )

    if not spa_index_available():
        return

    router = APIRouter(include_in_schema=False)

    @router.get("/admin/ui/")
    def admin_spa_home() -> FileResponse:
        return serve_spa_index()

    for segment in SPA_SHELL_SEGMENTS:
        path = f"/admin/ui/{segment}"

        def admin_spa_shell(_path: str = path) -> FileResponse:
            return serve_spa_index()

        router.add_api_route(path, admin_spa_shell, methods=["GET"], include_in_schema=False)

    @router.get("/admin/ui/incidents/{incident_id}")
    def admin_spa_incident(incident_id: str) -> FileResponse:
        _ = incident_id
        return serve_spa_index()

    @router.get("/admin/ui/devices/{device_uuid}")
    def admin_spa_device(device_uuid: str) -> FileResponse:
        _ = device_uuid
        return serve_spa_index()

    for name in ("favicon.svg", "icons.svg"):
        file_path = SPA_DIR / name
        if not file_path.is_file():
            continue

        def _root_asset(fp: Path = file_path) -> FileResponse:
            return FileResponse(fp)

        router.add_api_route(
            f"/admin/ui/{name}",
            _root_asset,
            methods=["GET"],
            include_in_schema=False,
        )

    app.include_router(router)
