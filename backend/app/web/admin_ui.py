from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.data.countries import COUNTRY_MASTER
from app.db import get_session
from app.models.call_rule import CallRule
from app.models.country_restriction import CountryRestriction
from app.models.device import AppScanResult, Device
from app.services.call_rule_service import create_call_rule, delete_call_rule
from app.services.country_restriction_service import (
    create_country_restriction,
    delete_country_restriction,
    update_country_restriction,
)
from app.web.auth import login_redirect, logout_redirect, require_admin_ui

router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
APPLY_OPTIONS = ["call", "dns", "internet"]


def _ctx(request: Request, **kwargs):
    return {"request": request, "admin_authed": True, **kwargs}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    error = "Invalid API key" if request.query_params.get("error") else None
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"request": request, "admin_authed": False, "error": error},
    )


@router.post("/login")
def login_submit(api_key: str = Form(...)) -> RedirectResponse:
    from app.core.config import settings

    if api_key != settings.admin_api_key:
        return RedirectResponse("/admin/ui/login?error=1", status_code=303)
    return login_redirect(api_key)


@router.get("/logout")
def logout(_: str = Depends(require_admin_ui)) -> RedirectResponse:
    return logout_redirect()


@router.get("/restrictions", response_class=HTMLResponse)
def list_restrictions(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    rows = list(session.exec(select(CountryRestriction)).all())
    return templates.TemplateResponse(
        request, "admin/restrictions_list.html", _ctx(request, rows=rows)
    )


@router.get("/restrictions/new", response_class=HTMLResponse)
def new_restriction(request: Request, _: str = Depends(require_admin_ui)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/restriction_form.html",
        _ctx(
            request,
            row=None,
            countries=COUNTRY_MASTER,
            selected_countries=[],
            selected_apply=["call", "dns"],
            apply_options=APPLY_OPTIONS,
            action="/admin/ui/restrictions",
            error=None,
        ),
    )


@router.post("/restrictions")
def create_restriction_form(
    request: Request,
    name: str = Form(...),
    countries: list[str] = Form(...),
    apply_to: list[str] = Form(...),
    description: str = Form(""),
    enabled: str | None = Form(None),
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    country_list = countries if isinstance(countries, list) else [countries]
    apply_list = apply_to if isinstance(apply_to, list) else [apply_to]
    try:
        row = create_country_restriction(
            session,
            name=name,
            countries=country_list,
            apply_to=apply_list,
            enabled=enabled is not None,
            description=description or None,
        )
    except (TypeError, ValueError) as exc:
        return templates.TemplateResponse(
            request,
            "admin/restriction_form.html",
            _ctx(
                request,
                row=None,
                countries=COUNTRY_MASTER,
                selected_countries=country_list,
                selected_apply=apply_list,
                apply_options=APPLY_OPTIONS,
                action="/admin/ui/restrictions",
                error=str(exc),
            ),
            status_code=422,
        )
    return RedirectResponse(f"/admin/ui/restrictions/{row.id}", status_code=303)


@router.get("/restrictions/{restriction_id}", response_class=HTMLResponse)
def edit_restriction(
    restriction_id: str,
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    row = session.get(CountryRestriction, restriction_id)
    if row is None:
        return RedirectResponse("/admin/ui/restrictions", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin/restriction_form.html",
        _ctx(
            request,
            row=row,
            countries=COUNTRY_MASTER,
            selected_countries=list(row.countries),
            selected_apply=list(row.apply_to),
            apply_options=APPLY_OPTIONS,
            action=f"/admin/ui/restrictions/{row.id}",
            error=None,
        ),
    )


@router.post("/restrictions/{restriction_id}")
def update_restriction_form(
    restriction_id: str,
    request: Request,
    name: str = Form(...),
    countries: list[str] = Form(...),
    apply_to: list[str] = Form(...),
    description: str = Form(""),
    enabled: str | None = Form(None),
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    country_list = countries if isinstance(countries, list) else [countries]
    apply_list = apply_to if isinstance(apply_to, list) else [apply_to]
    try:
        update_country_restriction(
            session,
            restriction_id,
            name=name,
            countries=country_list,
            apply_to=apply_list,
            enabled=enabled is not None,
            description=description or None,
        )
    except (TypeError, ValueError) as exc:
        row = session.get(CountryRestriction, restriction_id)
        return templates.TemplateResponse(
            request,
            "admin/restriction_form.html",
            _ctx(
                request,
                row=row,
                countries=COUNTRY_MASTER,
                selected_countries=country_list,
                selected_apply=apply_list,
                apply_options=APPLY_OPTIONS,
                action=f"/admin/ui/restrictions/{restriction_id}",
                error=str(exc),
            ),
            status_code=422,
        )
    return RedirectResponse(f"/admin/ui/restrictions/{restriction_id}", status_code=303)


@router.post("/restrictions/{restriction_id}/delete")
def delete_restriction_form(
    restriction_id: str,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    delete_country_restriction(session, restriction_id)
    return RedirectResponse("/admin/ui/restrictions", status_code=303)


def _parse_lines(raw: str) -> list[str]:
    return [line.strip() for line in raw.replace(",", "\n").splitlines() if line.strip()]


@router.get("/call-rules", response_class=HTMLResponse)
def list_call_rules_ui(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    rows = list(session.exec(select(CallRule)).all())
    return templates.TemplateResponse(
        request,
        "admin/call_rules.html",
        _ctx(request, rows=rows, error=None, whitelist_text="", country_codes_text=""),
    )


@router.post("/call-rules")
def create_call_rule_form(
    request: Request,
    whitelist: str = Form(...),
    country_codes: str = Form(""),
    enabled: str | None = Form(None),
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    wl = _parse_lines(whitelist)
    codes = _parse_lines(country_codes)
    try:
        if not wl:
            raise ValueError("whitelist requires at least one full number")
        create_call_rule(
            session,
            country_codes=codes,
            whitelist=wl,
            enabled=enabled is not None,
        )
    except (TypeError, ValueError) as exc:
        rows = list(session.exec(select(CallRule)).all())
        return templates.TemplateResponse(
            request,
            "admin/call_rules.html",
            _ctx(
                request,
                rows=rows,
                error=str(exc),
                whitelist_text=whitelist,
                country_codes_text=country_codes,
            ),
            status_code=422,
        )
    return RedirectResponse("/admin/ui/call-rules", status_code=303)


@router.post("/call-rules/{rule_id}/delete")
def delete_call_rule_form(
    rule_id: str,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    delete_call_rule(session, rule_id)
    return RedirectResponse("/admin/ui/call-rules", status_code=303)


@router.get("/devices", response_class=HTMLResponse)
def list_devices(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    devices = list(session.exec(select(Device)).all())
    return templates.TemplateResponse(
        request, "admin/devices.html", _ctx(request, devices=devices)
    )


@router.get("/devices/{device_uuid}/scans", response_class=HTMLResponse)
def device_scans(
    device_uuid: str,
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    scans = list(
        session.exec(select(AppScanResult).where(AppScanResult.device_uuid == device_uuid)).all()
    )
    return templates.TemplateResponse(
        request,
        "admin/scans.html",
        _ctx(request, device_uuid=device_uuid, scans=scans),
    )
