from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from app.api.deps import require_device
from app.db import get_session
from app.models.device import AppAllowlist, AppScanResult, Device, DeviceHealthEvent
from app.services.admin_notify import notify_admin
from app.services.rule_bundle_builder import build_rule_bundle

router = APIRouter(prefix="/api/v1", tags=["device"], dependencies=[Depends(require_device)])


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
def rules_latest(session: Session = Depends(get_session)) -> dict:
    return build_rule_bundle(session)


@router.post("/devices/heartbeat", response_model=HeartbeatOut)
def heartbeat(body: HeartbeatIn, session: Session = Depends(get_session)) -> Device:
    now = datetime.now(timezone.utc)
    device = session.get(Device, body.device_uuid)
    prev_screening = device.call_screening_enabled if device is not None else False
    if device is None:
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

    if prev_screening and not body.call_screening_enabled:
        peers = ",".join(body.call_screening_peers) if body.call_screening_peers else ""
        session.add(
            DeviceHealthEvent(
                device_uuid=body.device_uuid,
                type="role_lost",
                detail=f"peers={peers}" if peers else None,
                created_at=now,
            )
        )
        notify_admin(f"ElderShield role_lost device={body.device_uuid} peers={peers}")

    session.commit()
    session.refresh(device)
    return device


@router.post("/devices/health-events")
def health_events(body: HealthEventsIn, session: Session = Depends(get_session)) -> dict:
    if session.get(Device, body.device_uuid) is None:
        session.add(Device(device_uuid=body.device_uuid, last_sync_at=datetime.now(timezone.utc)))
        session.commit()
    saved = 0
    for ev in body.events:
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
def scan_result(body: ScanResultIn, session: Session = Depends(get_session)) -> dict:
    if session.get(Device, body.device_uuid) is None:
        session.add(Device(device_uuid=body.device_uuid, last_sync_at=datetime.now(timezone.utc)))
        session.commit()
    allowed = {
        row.package_name for row in session.exec(select(AppAllowlist)).all()
    }
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
