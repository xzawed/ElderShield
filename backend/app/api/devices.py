from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, col, select

from app.api.deps import DeviceAuth, assert_device_uuid_bound, require_device
from app.api.schemas import IncidentIn, IncidentOut
from app.db import get_session
from app.models.device import AppAllowlist, AppScanResult, Device, DeviceHealthEvent
from app.models.incident import Incident
from app.services.admin_notify import notify_admin
from app.services.incident_merge import (
    IncidentSanitizeError,
    merge_payloads,
    purge_old_incidents,
    sanitize_calls,
    should_merge,
    strip_raw_phone_keys,
)
from app.services.rule_bundle_builder import build_rule_bundle

router = APIRouter(prefix="/api/v1", tags=["device"])


def _compute_degraded(
    *,
    dns_configured: bool,
    call_screening_enabled: bool,
    last_sync_ok: bool,
) -> bool:
    return (not dns_configured) or (not call_screening_enabled) or (not last_sync_ok)


class HeartbeatIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_uuid: str = Field(alias="deviceUuid")
    app_version: str = Field(alias="appVersion")
    dns_configured: bool = Field(alias="dnsConfigured")
    call_screening_enabled: bool = Field(alias="callScreeningEnabled")
    call_screening_held_by: str | None = Field(default=None, alias="callScreeningHeldBy")
    call_screening_peers: list[str] = Field(default_factory=list, alias="callScreeningPeers")
    last_rule_version: int = Field(alias="lastRuleVersion")
    dns_host_class: str | None = Field(default=None, alias="dnsHostClass")
    last_sync_ok: bool = Field(default=True, alias="lastSyncOk")
    last_sync_error_code: str | None = Field(default=None, alias="lastSyncErrorCode")
    cached_bundle_version: int = Field(default=0, alias="cachedBundleVersion")
    protection_degraded: bool | None = Field(default=None, alias="protectionDegraded")


class HeartbeatOut(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True, from_attributes=True, ser_json_by_alias=True
    )

    device_uuid: str = Field(serialization_alias="deviceUuid")
    last_sync_at: datetime = Field(serialization_alias="lastSyncAt")
    app_version: str = Field(serialization_alias="appVersion")


class HealthEventIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    detail: str | None = None
    at: datetime | None = None


class HealthEventsIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_uuid: str = Field(alias="deviceUuid")
    events: list[HealthEventIn]


class SuspiciousAppIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    package_name: str = Field(alias="packageName")
    installer: str | None = None
    dangerous_permissions: list[str] = Field(default_factory=list, alias="dangerousPermissions")
    risk_score: int = Field(alias="riskScore")
    reasons: list[str] = Field(default_factory=list)


class ScanResultIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_uuid: str = Field(alias="deviceUuid")
    suspicious_apps: list[SuspiciousAppIn] = Field(alias="suspiciousApps")


@router.get("/rules/latest")
def rules_latest(
    session: Session = Depends(get_session),
    _auth: DeviceAuth = Depends(require_device),
) -> dict:
    return build_rule_bundle(session)


@router.post("/devices/heartbeat", response_model=HeartbeatOut)
def heartbeat(
    body: HeartbeatIn,
    session: Session = Depends(get_session),
    auth: DeviceAuth = Depends(require_device),
) -> Device:
    assert_device_uuid_bound(auth, body.device_uuid)
    now = datetime.now(timezone.utc)
    device = session.get(Device, body.device_uuid)
    prev_screening = device.call_screening_enabled if device is not None else False
    if device is None:
        # Token-bound callers already have a row from enroll; shared lab key may mint.
        if not auth.shared_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")
        device = Device(device_uuid=body.device_uuid)
    device.app_version = body.app_version
    device.dns_configured = body.dns_configured
    device.call_screening_enabled = body.call_screening_enabled
    device.call_screening_held_by = body.call_screening_held_by
    device.call_screening_peers = list(body.call_screening_peers)
    device.last_rule_version = body.last_rule_version
    device.last_sync_at = now
    device.dns_host_class = body.dns_host_class
    device.last_sync_ok = body.last_sync_ok
    device.last_sync_error_code = body.last_sync_error_code
    device.cached_bundle_version = body.cached_bundle_version
    device.protection_degraded = _compute_degraded(
        dns_configured=body.dns_configured,
        call_screening_enabled=body.call_screening_enabled,
        last_sync_ok=body.last_sync_ok,
    )
    session.add(device)

    if prev_screening and not body.call_screening_enabled and body.call_screening_peers:
        peers = ",".join(body.call_screening_peers)
        session.add(
            DeviceHealthEvent(
                device_uuid=body.device_uuid,
                type="role_lost",
                detail=f"peers={peers}",
                created_at=now,
            )
        )
        notify_admin(f"ElderShield role_lost device={body.device_uuid} peers={peers}")

    session.commit()
    session.refresh(device)
    return device


_ALLOWED_HEALTH_TYPES = frozenset({"dns_drift", "role_lost", "sync_failed"})


@router.post("/devices/health-events")
def health_events(
    body: HealthEventsIn,
    session: Session = Depends(get_session),
    auth: DeviceAuth = Depends(require_device),
) -> dict:
    assert_device_uuid_bound(auth, body.device_uuid)
    if session.get(Device, body.device_uuid) is None:
        if not auth.shared_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")
        session.add(Device(device_uuid=body.device_uuid, last_sync_at=datetime.now(timezone.utc)))
        session.commit()
    saved = 0
    for ev in body.events:
        if ev.type not in _ALLOWED_HEALTH_TYPES:
            continue
        at = ev.at or datetime.now(timezone.utc)
        session.add(
            DeviceHealthEvent(
                device_uuid=body.device_uuid,
                type=ev.type,
                detail=ev.detail,
                created_at=at,
            )
        )
        saved += 1
        if ev.type in ("dns_drift", "role_lost"):
            notify_admin(
                f"ElderShield {ev.type} device={body.device_uuid} detail={ev.detail or ''}"
            )
    session.commit()
    return {"ok": True, "saved": saved}


@router.post("/devices/apps/scan-result")
def scan_result(
    body: ScanResultIn,
    session: Session = Depends(get_session),
    auth: DeviceAuth = Depends(require_device),
) -> dict:
    assert_device_uuid_bound(auth, body.device_uuid)
    if session.get(Device, body.device_uuid) is None:
        if not auth.shared_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")
        session.add(Device(device_uuid=body.device_uuid, last_sync_at=datetime.now(timezone.utc)))
        session.commit()
    allowed = {row.package_name for row in session.exec(select(AppAllowlist)).all()}
    saved = 0
    for app in body.suspicious_apps:
        if app.package_name in allowed:
            continue
        session.add(
            AppScanResult(
                device_uuid=body.device_uuid,
                package_name=app.package_name,
                installer=app.installer,
                dangerous_permissions=list(app.dangerous_permissions),
                risk_score=app.risk_score,
                reasons=list(app.reasons),
            )
        )
        saved += 1
        if app.risk_score >= 80:
            notify_admin(
                f"ElderShield high-risk app device={body.device_uuid} "
                f"pkg={app.package_name} score={app.risk_score}"
            )
    session.commit()
    return {"ok": True, "saved": saved}


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ensure_device(session: Session, auth: DeviceAuth, device_uuid: str) -> None:
    if session.get(Device, device_uuid) is None:
        if not auth.shared_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device_not_found")
        session.add(Device(device_uuid=device_uuid, last_sync_at=datetime.now(timezone.utc)))
        session.commit()


def _incident_payload(body: IncidentIn, calls: list[dict]) -> dict:
    payload: dict = {
        "apps": list(body.apps or []),
        "calls": calls,
        "dns": dict(body.dns or {}),
        "triggers": list(body.triggers or []),
    }
    if body.window is not None:
        payload["window"] = body.window
    if body.country_hints is not None:
        payload["countryHints"] = body.country_hints
    if body.protection_snapshot is not None:
        payload["protectionSnapshot"] = body.protection_snapshot
    return strip_raw_phone_keys(payload)


@router.post("/devices/incidents", response_model=IncidentOut)
def post_incident(
    body: IncidentIn,
    response: Response,
    session: Session = Depends(get_session),
    auth: DeviceAuth = Depends(require_device),
) -> IncidentOut:
    assert_device_uuid_bound(auth, body.device_uuid)
    try:
        calls = sanitize_calls(body.calls)
    except IncidentSanitizeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    purge_old_incidents(session, days=90)
    _ensure_device(session, auth, body.device_uuid)

    incoming = _incident_payload(body, calls)
    triggered_at = _as_utc(body.triggered_at)

    existing = session.get(Incident, body.incident_id)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        session.commit()
        return IncidentOut.from_row(existing)

    latest = session.exec(
        select(Incident)
        .where(Incident.device_uuid == body.device_uuid)
        .order_by(col(Incident.triggered_at).desc())
    ).first()
    if latest is not None and should_merge(_as_utc(latest.triggered_at), triggered_at):
        merged = merge_payloads(latest.payload or {}, incoming)
        latest.payload = strip_raw_phone_keys(merged)
        latest.triggers = list(merged.get("triggers") or [])
        latest_at = _as_utc(latest.triggered_at)
        if triggered_at > latest_at:
            latest.triggered_at = triggered_at
        session.add(latest)
        session.commit()
        session.refresh(latest)
        response.status_code = status.HTTP_200_OK
        return IncidentOut.from_row(latest)

    row = Incident(
        id=body.incident_id,
        device_uuid=body.device_uuid,
        triggered_at=triggered_at,
        triggers=list(body.triggers or []),
        payload=incoming,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    response.status_code = status.HTTP_201_CREATED
    return IncidentOut.from_row(row)
