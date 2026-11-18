from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.api.deps import require_device
from app.db import get_session
from app.models.device import AppScanResult, Device
from app.services.rule_bundle_builder import build_rule_bundle

router = APIRouter(prefix="/api/v1", tags=["device"], dependencies=[Depends(require_device)])


class HeartbeatIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_uuid: str = Field(alias="deviceUuid")
    app_version: str = Field(alias="appVersion")
    dns_configured: bool = Field(alias="dnsConfigured")
    call_screening_enabled: bool = Field(alias="callScreeningEnabled")
    last_rule_version: int = Field(alias="lastRuleVersion")


class HeartbeatOut(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True, from_attributes=True, ser_json_by_alias=True
    )

    device_uuid: str = Field(serialization_alias="deviceUuid")
    last_sync_at: datetime = Field(serialization_alias="lastSyncAt")
    app_version: str = Field(serialization_alias="appVersion")


class SuspiciousAppIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    package_name: str = Field(alias="packageName")
    installer: str | None = None
    dangerous_permissions: list[str] = Field(default_factory=list, alias="dangerousPermissions")
    risk_score: int = Field(alias="riskScore")


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
    if device is None:
        device = Device(device_uuid=body.device_uuid)
    device.app_version = body.app_version
    device.dns_configured = body.dns_configured
    device.call_screening_enabled = body.call_screening_enabled
    device.last_rule_version = body.last_rule_version
    device.last_sync_at = now
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.post("/devices/apps/scan-result")
def scan_result(body: ScanResultIn, session: Session = Depends(get_session)) -> dict:
    if session.get(Device, body.device_uuid) is None:
        session.add(Device(device_uuid=body.device_uuid, last_sync_at=datetime.now(timezone.utc)))
        session.commit()
    for app in body.suspicious_apps:
        session.add(
            AppScanResult(
                device_uuid=body.device_uuid,
                package_name=app.package_name,
                installer=app.installer,
                dangerous_permissions=list(app.dangerous_permissions),
                risk_score=app.risk_score,
            )
        )
    session.commit()
    return {"ok": True, "saved": len(body.suspicious_apps)}
