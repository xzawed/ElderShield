from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.devices import router as device_router
from app.core.config import assert_secure_settings, settings
from app.db import init_db
from app.web.admin_ui import router as admin_ui_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    assert_secure_settings(settings)
    init_db()
    yield


app = FastAPI(title="ElderShield API", version="0.1.0", lifespan=lifespan)
app.include_router(admin_router)
app.include_router(device_router)
app.include_router(admin_ui_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
