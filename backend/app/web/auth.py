"""Admin UI session — never store the raw API key in the browser cookie."""

import hashlib
import hmac
import os

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.core.config import settings

COOKIE_NAME = "eldershield_admin_session"
COOKIE_PATH = "/"
# SPA must send this on cookie-authenticated /api/v1/admin/* calls (CSRF mitigation).
ADMIN_UI_REQUEST_HEADER = "X-ElderShield-Admin"
ADMIN_UI_REQUEST_HEADER_VALUE = "1"


def _cookie_secure() -> bool:
    return os.getenv("COOKIE_SECURE", "").lower() in ("1", "true", "yes")


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


def cookie_auth_csrf_ok(request: Request) -> bool:
    """Reject cookie-only admin API use without SPA custom header (blocks top-level CSRF GET)."""
    return request.headers.get(ADMIN_UI_REQUEST_HEADER) == ADMIN_UI_REQUEST_HEADER_VALUE


def require_admin_ui(request: Request) -> str:
    key = admin_key_from_request(request)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/ui/login"},
        )
    return key


def set_admin_session_cookie(response: Response, api_key: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        session_token_for(api_key),
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path=COOKIE_PATH,
        max_age=60 * 60 * 12,
    )


def clear_admin_session_cookie(response: Response) -> None:
    """Must mirror set_admin_session_cookie flags or browsers keep Secure cookies."""
    response.delete_cookie(
        COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )


def login_redirect(api_key: str) -> RedirectResponse:
    from app.web.spa import spa_home_path

    resp = RedirectResponse(spa_home_path(), status_code=303)
    set_admin_session_cookie(resp, api_key)
    return resp


def logout_redirect() -> RedirectResponse:
    resp = RedirectResponse("/admin/ui/login", status_code=303)
    clear_admin_session_cookie(resp)
    return resp
