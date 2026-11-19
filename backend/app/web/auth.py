"""Admin UI session — never store the raw API key in the browser cookie."""

import hashlib
import hmac
import os

from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.config import settings

COOKIE_NAME = "eldershield_admin_session"


def session_token_for(api_key: str) -> str:
    return hmac.new(
        api_key.encode("utf-8"),
        b"eldershield-admin-ui-v1",
        hashlib.sha256,
    ).hexdigest()


def admin_key_from_request(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    expected = session_token_for(settings.admin_api_key)
    if not hmac.compare_digest(token, expected):
        return None
    return settings.admin_api_key


def require_admin_ui(request: Request) -> str:
    key = admin_key_from_request(request)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/ui/login"},
        )
    return key


def login_redirect(api_key: str) -> RedirectResponse:
    resp = RedirectResponse("/admin/ui/restrictions", status_code=303)
    secure = os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")
    resp.set_cookie(
        COOKIE_NAME,
        session_token_for(api_key),
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=60 * 60 * 12,
    )
    return resp


def logout_redirect() -> RedirectResponse:
    resp = RedirectResponse("/admin/ui/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp
