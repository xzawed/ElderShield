from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.core.config import settings

COOKIE_NAME = "eldershield_admin_key"


def admin_key_from_request(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


def require_admin_ui(request: Request) -> str:
    key = admin_key_from_request(request)
    if not key or key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/admin/ui/login"},
        )
    return key


def login_redirect(api_key: str) -> RedirectResponse:
    resp = RedirectResponse("/admin/ui/restrictions", status_code=303)
    resp.set_cookie(COOKIE_NAME, api_key, httponly=True, samesite="lax")
    return resp


def logout_redirect() -> RedirectResponse:
    resp = RedirectResponse("/admin/ui/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp
