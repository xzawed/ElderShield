from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlmodel import Session, func, select

from app.api.admin import router as admin_router
from app.api.devices import router as device_router
from app.api.enroll import router as enroll_router
from app.core.config import assert_secure_settings, settings
from app import db as db_module
from app.db import init_db
from app.models.device import Device
from app.models.rule_bundle_meta import SINGLETON_ID, RuleBundleMeta
from app.web.admin_ui import router as admin_ui_router
from app.web.spa import register_admin_spa, spa_home_path, spa_index_available


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_secure_settings(settings)
    init_db()
    yield


app = FastAPI(title="ElderShield API", version="0.2.0", lifespan=lifespan)
register_admin_spa(app)
app.include_router(admin_router)
app.include_router(device_router)
app.include_router(enroll_router)
app.include_router(admin_ui_router)


@app.get("/")
def root() -> RedirectResponse:
    """Public Railway / GitHub About URL → admin UI."""
    return RedirectResponse(url=spa_home_path(), status_code=302)


@app.get("/admin")
@app.get("/admin/ui")
def admin_entry() -> RedirectResponse:
    if spa_index_available():
        return RedirectResponse(url="/admin/ui/", status_code=302)
    return RedirectResponse(url="/admin/ui/login", status_code=302)


@app.get("/health")
def health() -> dict:
    with Session(db_module.engine) as session:
        devices = session.exec(select(func.count()).select_from(Device)).one()
        degraded = session.exec(
            select(func.count()).select_from(Device).where(Device.protection_degraded.is_(True))
        ).one()
        meta = session.get(RuleBundleMeta, SINGLETON_ID)
        bundle_version = int(meta.version) if meta is not None else 0
        seen = [ts for ts in session.exec(select(Device.last_sync_at)).all() if ts is not None]
    now = datetime.now(timezone.utc)
    last_seen = max(seen) if seen else None
    lag = None
    last_iso = None
    if last_seen is not None:
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        last_iso = last_seen.isoformat()
        lag = max(0, int((now - last_seen).total_seconds()))
    return {
        "status": "ok",
        "devices": int(devices or 0),
        "degradedDevices": int(degraded or 0),
        "bundleVersion": bundle_version,
        "lastSeenAt": last_iso,
        "syncLagSeconds": lag,
    }
