from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status
from sqlmodel import Session, select

from app.core.config import settings
from app.db import get_session
from app.models.device import Device
from app.services.device_tokens import hash_device_token
from app.web.auth import admin_key_from_request, cookie_auth_csrf_ok


@dataclass(frozen=True)
class DeviceAuth:
    """Authenticated device caller.

    shared_key=True: lab fleet key — any deviceUuid in body is allowed.
    shared_key=False: bound_device_uuid must match body deviceUuid.
    """

    shared_key: bool
    bound_device_uuid: str | None


def require_admin(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    if x_api_key is not None and x_api_key != "":
        if x_api_key == settings.device_api_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin key required")
        if x_api_key != settings.admin_api_key:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
        return
    if admin_key_from_request(request) is not None:
        if not cookie_auth_csrf_ok(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing admin UI request header",
            )
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")


def require_device(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: Session = Depends(get_session),
) -> DeviceAuth:
    if x_api_key is None or x_api_key == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if x_api_key == settings.device_api_key:
        return DeviceAuth(shared_key=True, bound_device_uuid=None)
    token_hash = hash_device_token(x_api_key)
    device = session.exec(select(Device).where(Device.api_token_hash == token_hash)).first()
    if device is None or device.token_revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device key required")
    return DeviceAuth(shared_key=False, bound_device_uuid=device.device_uuid)


def assert_device_uuid_bound(auth: DeviceAuth, device_uuid: str) -> None:
    if auth.bound_device_uuid is not None and device_uuid != auth.bound_device_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="device_uuid_mismatch",
        )
