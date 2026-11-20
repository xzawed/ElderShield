from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.db import get_session
from app.models.device import Device
from app.services.device_tokens import hash_device_token


def require_admin(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if x_api_key is None or x_api_key == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if x_api_key == settings.device_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin key required")
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


def require_device(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: Session = Depends(get_session),
) -> None:
    if x_api_key is None or x_api_key == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if x_api_key == settings.device_api_key:
        return
    token_hash = hash_device_token(x_api_key)
    device = session.exec(select(Device).where(Device.api_token_hash == token_hash)).first()
    if device is None or device.token_revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device key required")
