from pathlib import Path
import time

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, select

from app.api.schemas import IncidentOut
from app.data.countries import COUNTRY_MASTER
from app.db import get_session
from app.models.call_rule import CallRule
from app.models.country_restriction import CountryRestriction
from app.models.device import AppAllowlist, AppScanResult, AuditLog, Device, DeviceHealthEvent
from app.models.incident import Incident
from app.services.audit import record_audit
from app.services.call_rule_service import create_call_rule, delete_call_rule
from app.services.country_restriction_service import (
    create_country_restriction,
    delete_country_restriction,
    update_country_restriction,
)
from app.services.dns_denylist import build_dns_denylist
from app.services.incident_merge import strip_raw_phone_keys
from app.services.nextdns_logs import enrich_incident_dns
from app.web.auth import login_redirect, logout_redirect, require_admin_ui
from app.web.i18n import LANG_COOKIE, make_translator, normalize_lang, resolve_lang

router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
APPLY_OPTIONS = ["call", "dns", "internet"]

# Phase 2A — in-memory login rate limit (per process).
_LOGIN_FAILURES: dict[str, list[float]] = {}
_LOGIN_WINDOW_SEC = 600
_LOGIN_MAX_FAILURES = 10


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _login_blocked(ip: str) -> bool:
    now = time.time()
    stamps = [t for t in _LOGIN_FAILURES.get(ip, []) if now - t < _LOGIN_WINDOW_SEC]
    _LOGIN_FAILURES[ip] = stamps
    return len(stamps) >= _LOGIN_MAX_FAILURES


def _record_login_failure(ip: str) -> None:
    _LOGIN_FAILURES.setdefault(ip, []).append(time.time())


def _ctx(request: Request, admin_authed: bool = True, **kwargs):
    lang = resolve_lang(request)
    t = make_translator(lang)
    return {
        "request": request,
        "admin_authed": admin_authed,
        "lang": lang,
        "t": t,
        **kwargs,
    }


@router.get("/lang")
def set_lang(request: Request, set: str = "ko", next: str = "/admin/ui/restrictions") -> Response:
    lang = normalize_lang(set)
    # Only allow relative admin UI next paths (open-redirect guard).
    nxt = next if next.startswith("/admin/ui") else "/admin/ui/restrictions"
    resp = RedirectResponse(nxt, status_code=303)
    resp.set_cookie(
        LANG_COOKIE,
        lang,
        max_age=86400 * 365,
        httponly=False,
        samesite="lax",
        path="/",
    )
    return resp


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    lang = resolve_lang(request)
    t = make_translator(lang)
    err = request.query_params.get("error")
    if err == "rate":
        error = t("login.error_rate")
    elif err:
        error = t("login.error_invalid")
    else:
        error = None
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        _ctx(request, admin_authed=False, error=error),
    )


@router.post("/login")
def login_submit(request: Request, api_key: str = Form(...)) -> Response:
    import hmac

    from app.core.config import settings

    ip = _client_ip(request)
    if _login_blocked(ip):
        return RedirectResponse("/admin/ui/login?error=rate", status_code=303)

    expected = settings.admin_api_key or ""
    left = api_key.encode("utf-8")
    right = expected.encode("utf-8")
    # compare_digest requires equal length; unequal → reject without raising.
    if len(left) != len(right) or not hmac.compare_digest(left, right):
        _record_login_failure(ip)
        return RedirectResponse("/admin/ui/login?error=1", status_code=303)
    _LOGIN_FAILURES.pop(ip, None)
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
    record_audit(
        session,
        action="create",
        resource_type="country_restriction",
        resource_id=row.id,
        detail=row.name,
        commit=True,
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
    record_audit(
        session,
        action="update",
        resource_type="country_restriction",
        resource_id=restriction_id,
        commit=True,
    )
    return RedirectResponse(f"/admin/ui/restrictions/{restriction_id}", status_code=303)


@router.post("/restrictions/{restriction_id}/delete")
def delete_restriction_form(
    restriction_id: str,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    if delete_country_restriction(session, restriction_id):
        record_audit(
            session,
            action="delete",
            resource_type="country_restriction",
            resource_id=restriction_id,
            commit=True,
        )
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
        row = create_call_rule(
            session,
            country_codes=codes,
            whitelist=wl,
            enabled=enabled is not None,
        )
        record_audit(
            session,
            action="create",
            resource_type="call_rule",
            resource_id=row.id,
            commit=True,
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
    if delete_call_rule(session, rule_id):
        record_audit(
            session,
            action="delete",
            resource_type="call_rule",
            resource_id=rule_id,
            commit=True,
        )
    return RedirectResponse("/admin/ui/call-rules", status_code=303)


def _dns_denylist_page(
    request: Request,
    session: Session,
    *,
    sync_ok: bool | None = None,
    sync_message: str | None = None,
) -> HTMLResponse:
    rows = list(session.exec(select(CountryRestriction)).all())
    payload = build_dns_denylist(rows)
    return templates.TemplateResponse(
        request,
        "admin/dns_denylist.html",
        _ctx(
            request,
            countries=payload["countries"],
            tlds=payload["tlds"],
            domains=payload["domains"],
            sync_ok=sync_ok,
            sync_message=sync_message,
        ),
    )


@router.get("/dns-denylist", response_class=HTMLResponse)
def dns_denylist_ui(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    return _dns_denylist_page(request, session)


@router.post("/dns-denylist/sync-nextdns")
def dns_denylist_sync_nextdns(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
):
    from app.core.config import settings
    from app.services.nextdns_sync import NextDnsNotConfigured, NextDnsSyncError, sync_policy_to_nextdns

    rows = list(session.exec(select(CountryRestriction)).all())
    try:
        result = sync_policy_to_nextdns(
            rows,
            api_key=settings.nextdns_api_key,
            profile_id=settings.nextdns_profile_id,
        )
        msg = (
            f"Synced profile {result['profileId']}: "
            f"tlds={result['tlds'].get('desired')}, "
            f"denylist +{len(result['denylist'].get('added', []))} "
            f"-{len(result['denylist'].get('removed', []))}."
        )
        record_audit(
            session,
            action="sync_nextdns",
            resource_type="dns_denylist",
            resource_id=str(result["profileId"]),
            commit=True,
        )
        return _dns_denylist_page(request, session, sync_ok=True, sync_message=msg)
    except NextDnsNotConfigured as exc:
        return _dns_denylist_page(request, session, sync_ok=False, sync_message=str(exc))
    except NextDnsSyncError as exc:
        return _dns_denylist_page(request, session, sync_ok=False, sync_message=str(exc))


@router.get("/devices", response_class=HTMLResponse)
def list_devices(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    from app.services.enrollment_window import get_enrollment_window, is_enrollment_open

    devices = list(session.exec(select(Device)).all())
    role_lost = set(
        session.exec(
            select(DeviceHealthEvent.device_uuid).where(DeviceHealthEvent.type == "role_lost")
        ).all()
    )
    window = get_enrollment_window(session)
    return templates.TemplateResponse(
        request,
        "admin/devices.html",
        _ctx(
            request,
            devices=devices,
            role_lost=role_lost,
            enrollment_open=is_enrollment_open(session),
            enrollment_expires_at=window.expires_at,
        ),
    )


@router.post("/devices/enrollment-window")
def ui_set_enrollment_window(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
    enabled: str = Form("0"),
    ttl_minutes: int = Form(30),
) -> RedirectResponse:
    from app.services.enrollment_window import close_enrollment, open_enrollment

    if enabled in ("1", "true", "on", "yes"):
        open_enrollment(session, minutes=ttl_minutes)
    else:
        close_enrollment(session)
    return RedirectResponse("/admin/ui/devices", status_code=303)


@router.post("/devices/{device_uuid}/revoke-token")
def ui_revoke_device_token(
    device_uuid: str,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    from datetime import datetime, timezone

    device = session.get(Device, device_uuid)
    if device is None:
        return RedirectResponse("/admin/ui/devices", status_code=303)
    device.token_revoked_at = datetime.now(timezone.utc)
    device.api_token_hash = None
    session.add(device)
    record_audit(
        session,
        action="device_token_revoke",
        resource_type="device",
        resource_id=device_uuid,
        detail="token revoked via admin UI",
    )
    session.commit()
    return RedirectResponse(f"/admin/ui/devices/{device_uuid}", status_code=303)


@router.get("/devices/{device_uuid}", response_class=HTMLResponse)
def device_detail(
    device_uuid: str,
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    device = session.get(Device, device_uuid)
    if device is None:
        return RedirectResponse("/admin/ui/devices", status_code=303)
    events = list(
        session.exec(
            select(DeviceHealthEvent)
            .where(DeviceHealthEvent.device_uuid == device_uuid)
            .order_by(col(DeviceHealthEvent.created_at).desc())
            .limit(50)
        ).all()
    )
    scans = list(
        session.exec(
            select(AppScanResult)
            .where(AppScanResult.device_uuid == device_uuid)
            .order_by(col(AppScanResult.created_at).desc())
            .limit(50)
        ).all()
    )
    incidents = list(
        session.exec(
            select(Incident)
            .where(Incident.device_uuid == device_uuid)
            .order_by(col(Incident.triggered_at).desc())
            .limit(50)
        ).all()
    )
    allow = {
        r.package_name
        for r in session.exec(select(AppAllowlist)).all()
    }
    return templates.TemplateResponse(
        request,
        "admin/device_detail.html",
        _ctx(
            request,
            device=device,
            events=events,
            scans=scans,
            allowlist=allow,
            incidents=incidents,
        ),
    )


@router.get("/incidents/{incident_id}/export")
def incident_export(
    incident_id: str,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> JSONResponse:
    row = session.get(Incident, incident_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    body = IncidentOut.from_row(row).model_dump(by_alias=True, mode="json")
    body = strip_raw_phone_keys(body)
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    enriched = strip_raw_phone_keys(enrich_incident_dns(payload))
    body["payload"] = enriched
    before_avail = bool((payload.get("dns") or {}).get("available")) if isinstance(payload.get("dns"), dict) else False
    after_avail = bool((enriched.get("dns") or {}).get("available")) if isinstance(enriched.get("dns"), dict) else False
    if after_avail and not before_avail:
        row.payload = enriched
        session.add(row)
        session.commit()
    return JSONResponse(
        content=body,
        headers={
            "Content-Disposition": f'attachment; filename="incident-{incident_id}.json"',
        },
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


@router.get("/allowlist", response_class=HTMLResponse)
def allowlist_page(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    rows = list(session.exec(select(AppAllowlist)).all())
    return templates.TemplateResponse(
        request, "admin/allowlist.html", _ctx(request, rows=rows, error=None)
    )


@router.post("/allowlist")
def allowlist_add(
    package_name: str = Form(...),
    note: str = Form(""),
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    pkg = package_name.strip()
    row = session.get(AppAllowlist, pkg)
    if row is None:
        row = AppAllowlist(package_name=pkg, note=note or None)
    else:
        row.note = note or None
    session.add(row)
    record_audit(
        session,
        action="upsert",
        resource_type="app_allowlist",
        resource_id=pkg,
        detail=note or None,
    )
    session.commit()
    return RedirectResponse("/admin/ui/allowlist", status_code=303)


@router.post("/allowlist/{package_name}/delete")
def allowlist_delete(
    package_name: str,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> RedirectResponse:
    row = session.get(AppAllowlist, package_name)
    if row is not None:
        session.delete(row)
        record_audit(
            session,
            action="delete",
            resource_type="app_allowlist",
            resource_id=package_name,
        )
        session.commit()
    return RedirectResponse("/admin/ui/allowlist", status_code=303)


@router.get("/audit", response_class=HTMLResponse)
def audit_page(
    request: Request,
    _: str = Depends(require_admin_ui),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    rows = list(
        session.exec(select(AuditLog).order_by(col(AuditLog.created_at).desc()).limit(100)).all()
    )
    return templates.TemplateResponse(
        request, "admin/audit.html", _ctx(request, rows=rows)
    )
