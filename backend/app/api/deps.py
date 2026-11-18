from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_admin(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if x_api_key is None or x_api_key == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if x_api_key == settings.device_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin key required")
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")


def require_device(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if x_api_key is None or x_api_key == "":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if x_api_key != settings.device_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device key required")
