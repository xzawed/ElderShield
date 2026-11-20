from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, col, select

from app.api.deps import require_admin
from app.api.schemas import (
    CallRuleCreate,
    CallRuleOut,
    CountryMasterOut,
    CountryRestrictionCreate,
    CountryRestrictionOut,
    CountryRestrictionUpdate,
    DeviceOut,
    DnsDenylistOut,
    NextDnsSyncOut,
    RulesRollbackOut,
    RulesRollbackRequest,
)
from app.core.config import settings
from app.data.countries import COUNTRY_MASTER
from app.db import get_session
from app.models.call_rule import CallRule
from app.models.country_restriction import CountryRestriction
from datetime import datetime, timezone

from app.models.device import AppAllowlist, AppScanResult, AuditLog, Device, DeviceHealthEvent
from app.services.audit import record_audit
from app.services.call_rule_service import create_call_rule
from app.services.country_restriction_service import (
    create_country_restriction,
    delete_country_restriction,
    update_country_restriction,
)
from app.services.dns_denylist import build_dns_denylist
from app.services.enrollment_window import (
    DEFAULT_TTL_MINUTES,
    close_enrollment,
    get_enrollment_window,
    open_enrollment,
)
from app.services.nextdns_sync import NextDnsNotConfigured, NextDnsSyncError, sync_policy_to_nextdns
from app.services.rule_bundle_service import publish_rollback

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class AllowlistIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    package_name: str = Field(alias="packageName")
    note: str | None = None


class EnrollmentWindowIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool
    ttl_minutes: int = Field(default=DEFAULT_TTL_MINUTES, alias="ttlMinutes")


class EnrollmentWindowOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    enabled: bool
    open: bool
    expires_at: datetime | None = Field(default=None, serialization_alias="expiresAt")


@router.get("/countries", response_model=list[CountryMasterOut])
def list_countries() -> list[CountryMasterOut]:
    return [
        CountryMasterOut(
            code=c["code"],
            name=c.get("name_en") or c.get("name") or c["code"],
            nameEn=c.get("name_en") or c.get("name") or c["code"],
            nameKo=c.get("name_ko") or c.get("name_en") or c["code"],
            callingCode=c.get("calling_code") or "",
        )
        for c in COUNTRY_MASTER
    ]


@router.get("/country-restrictions", response_model=list[CountryRestrictionOut])
def list_restrictions(session: Session = Depends(get_session)) -> list[CountryRestriction]:
    return list(session.exec(select(CountryRestriction)).all())


@router.post(
    "/country-restrictions",
    response_model=CountryRestrictionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_restriction(
    body: CountryRestrictionCreate, session: Session = Depends(get_session)
) -> CountryRestriction:
    try:
        row = create_country_restriction(
            session,
            name=body.name,
            countries=body.countries,
            apply_to=body.apply_to,
            enabled=body.enabled,
            description=body.description,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_audit(
        session,
        action="create",
        resource_type="country_restriction",
        resource_id=row.id,
        detail=row.name,
        commit=True,
    )
    return row


@router.put("/country-restrictions/{restriction_id}", response_model=CountryRestrictionOut)
def put_restriction(
    restriction_id: str,
    body: CountryRestrictionUpdate,
    session: Session = Depends(get_session),
) -> CountryRestriction:
    patch = body.model_dump(exclude_unset=True, by_alias=False)
    if "apply_to" not in patch and "applyTo" in body.model_dump(exclude_unset=True, by_alias=True):
        patch["apply_to"] = body.apply_to
    try:
        updated = update_country_restriction(session, restriction_id, **patch)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Not found")
    record_audit(
        session,
        action="update",
        resource_type="country_restriction",
        resource_id=restriction_id,
        commit=True,
    )
    return updated


@router.delete("/country-restrictions/{restriction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restriction(
    restriction_id: str, session: Session = Depends(get_session)
) -> Response:
    if not delete_country_restriction(session, restriction_id):
        raise HTTPException(status_code=404, detail="Not found")
    record_audit(
        session,
        action="delete",
        resource_type="country_restriction",
        resource_id=restriction_id,
        commit=True,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/call-rules", response_model=list[CallRuleOut])
def list_call_rules(session: Session = Depends(get_session)) -> list[CallRule]:
    return list(session.exec(select(CallRule)).all())


@router.post("/call-rules", response_model=CallRuleOut, status_code=status.HTTP_201_CREATED)
def post_call_rule(
    body: CallRuleCreate, session: Session = Depends(get_session)
) -> CallRule:
    try:
        row = create_call_rule(
            session,
            country_codes=body.country_codes,
            whitelist=body.whitelist,
            enabled=body.enabled,
        )
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    record_audit(
        session,
        action="create",
        resource_type="call_rule",
        resource_id=row.id,
        commit=True,
    )
    return row


@router.post("/rules/rollback", response_model=RulesRollbackOut)
def rollback_rules(
    body: RulesRollbackRequest, session: Session = Depends(get_session)
) -> RulesRollbackOut:
    try:
        result = publish_rollback(
            session,
            target_restriction_version=body.target_version,
            restriction_id=body.restriction_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    row = result["restriction"]
    assert isinstance(row, CountryRestriction)
    record_audit(
        session,
        action="rollback",
        resource_type="country_restriction",
        resource_id=row.id,
        detail=f"targetVersion={body.target_version}",
        commit=True,
    )
    return RulesRollbackOut(
        id=row.id,
        name=row.name,
        countries=list(row.countries),
        apply_to=list(row.apply_to),
        enabled=row.enabled,
        version=row.version,
        description=row.description,
        bundle_version=int(result["bundle_version"]),
    )


@router.get("/dns-denylist", response_model=DnsDenylistOut)
def get_dns_denylist(session: Session = Depends(get_session)) -> DnsDenylistOut:
    rows = list(session.exec(select(CountryRestriction)).all())
    payload = build_dns_denylist(rows)
    return DnsDenylistOut(**payload)


@router.post("/dns-denylist/sync-nextdns", response_model=NextDnsSyncOut)
def sync_dns_denylist_nextdns(session: Session = Depends(get_session)) -> NextDnsSyncOut:
    rows = list(session.exec(select(CountryRestriction)).all())
    try:
        result = sync_policy_to_nextdns(
            rows,
            api_key=settings.nextdns_api_key,
            profile_id=settings.nextdns_profile_id,
        )
    except NextDnsNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except NextDnsSyncError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record_audit(
        session,
        action="sync_nextdns",
        resource_type="dns_denylist",
        resource_id=str(result["profileId"]),
        commit=True,
    )
    return NextDnsSyncOut(
        ok=True,
        profile_id=str(result["profileId"]),
        plan=DnsDenylistOut(**result["plan"]),
        tlds=result["tlds"],
        denylist=result["denylist"],
    )


@router.get("/enrollment-window", response_model=EnrollmentWindowOut)
def read_enrollment_window(session: Session = Depends(get_session)) -> EnrollmentWindowOut:
    from app.services.enrollment_window import is_enrollment_open

    row = get_enrollment_window(session)
    return EnrollmentWindowOut(
        enabled=row.enabled,
        open=is_enrollment_open(session),
        expires_at=row.expires_at,
    )


@router.post("/enrollment-window", response_model=EnrollmentWindowOut)
def set_enrollment_window(
    body: EnrollmentWindowIn, session: Session = Depends(get_session)
) -> EnrollmentWindowOut:
    from app.services.enrollment_window import is_enrollment_open

    if body.enabled:
        row = open_enrollment(session, minutes=body.ttl_minutes)
    else:
        row = close_enrollment(session)
    record_audit(
        session,
        action="enrollment_window_set",
        resource_type="enrollment_window",
        resource_id="default",
        detail=f"enabled={body.enabled} ttlMinutes={body.ttl_minutes}",
    )
    return EnrollmentWindowOut(
        enabled=row.enabled,
        open=is_enrollment_open(session),
        expires_at=row.expires_at,
    )


@router.delete("/devices/{device_uuid}/token", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device_token(device_uuid: str, session: Session = Depends(get_session)) -> Response:
    device = session.get(Device, device_uuid)
    if device is None:
        raise HTTPException(status_code=404, detail="Not found")
    device.token_revoked_at = datetime.now(timezone.utc)
    device.api_token_hash = None
    session.add(device)
    record_audit(
        session,
        action="device_token_revoke",
        resource_type="device",
        resource_id=device_uuid,
        detail="token revoked",
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(session: Session = Depends(get_session)) -> list[Device]:
    return list(session.exec(select(Device)).all())


@router.get("/devices/{device_uuid}")
def get_device(device_uuid: str, session: Session = Depends(get_session)) -> dict:
    device = session.get(Device, device_uuid)
    if device is None:
        raise HTTPException(status_code=404, detail="Not found")
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
    return {
        "device": DeviceOut.model_validate(device).model_dump(by_alias=True),
        "healthEvents": [
            {
                "id": e.id,
                "type": e.type,
                "detail": e.detail,
                "createdAt": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "scans": [
            {
                "packageName": s.package_name,
                "installer": s.installer,
                "dangerousPermissions": list(s.dangerous_permissions or []),
                "riskScore": s.risk_score,
                "reasons": list(s.reasons or []),
                "createdAt": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scans
        ],
    }


@router.get("/devices/{device_uuid}/scan-results")
def list_scan_results(device_uuid: str, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(
        select(AppScanResult).where(AppScanResult.device_uuid == device_uuid)
    ).all()
    return [
        {
            "packageName": r.package_name,
            "installer": r.installer,
            "dangerousPermissions": list(r.dangerous_permissions),
            "riskScore": r.risk_score,
            "reasons": list(r.reasons or []),
        }
        for r in rows
    ]


@router.get("/app-allowlist")
def list_allowlist(session: Session = Depends(get_session)) -> list[dict]:
    rows = list(session.exec(select(AppAllowlist)).all())
    return [
        {
            "packageName": r.package_name,
            "note": r.note,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/app-allowlist", status_code=status.HTTP_201_CREATED)
def add_allowlist(body: AllowlistIn, session: Session = Depends(get_session)) -> dict:
    row = session.get(AppAllowlist, body.package_name)
    if row is None:
        row = AppAllowlist(package_name=body.package_name, note=body.note)
    else:
        row.note = body.note
    session.add(row)
    record_audit(
        session,
        action="upsert",
        resource_type="app_allowlist",
        resource_id=body.package_name,
        detail=body.note,
    )
    session.commit()
    return {"packageName": row.package_name, "note": row.note}


@router.delete("/app-allowlist/{package_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allowlist(package_name: str, session: Session = Depends(get_session)) -> Response:
    row = session.get(AppAllowlist, package_name)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(row)
    record_audit(
        session,
        action="delete",
        resource_type="app_allowlist",
        resource_id=package_name,
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit")
def list_audit(limit: int = 100, session: Session = Depends(get_session)) -> list[dict]:
    lim = max(1, min(limit, 500))
    rows = list(
        session.exec(
            select(AuditLog).order_by(col(AuditLog.created_at).desc()).limit(lim)
        ).all()
    )
    return [
        {
            "id": r.id,
            "actor": r.actor,
            "action": r.action,
            "resourceType": r.resource_type,
            "resourceId": r.resource_id,
            "detail": r.detail,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
