from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(SQLModel, table=True):
    __tablename__ = "device"

    device_uuid: str = Field(primary_key=True, max_length=128)
    name: Optional[str] = None
    model: Optional[str] = None
    app_version: str = "0.0.0"
    dns_configured: bool = False
    call_screening_enabled: bool = False
    # Package that holds ROLE_CALL_SCREENING when known (usually this app); null if we do not hold it.
    call_screening_held_by: Optional[str] = Field(default=None, max_length=256)
    # Other installed CallScreeningService packages (hint for Bitdefender 병행 — not authoritative role holder).
    call_screening_peers: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]")
    )
    last_rule_version: int = 0
    last_sync_at: Optional[datetime] = None
    # Phase 2C health snapshot
    dns_host_class: Optional[str] = Field(default=None, max_length=32)
    last_sync_ok: bool = True
    last_sync_error_code: Optional[str] = Field(default=None, max_length=64)
    cached_bundle_version: int = 0
    protection_degraded: bool = False
    # Per-device API token (SHA-256 hex). Null = lab shared DEVICE_API_KEY only.
    api_token_hash: Optional[str] = Field(default=None, max_length=64, index=True)
    token_revoked_at: Optional[datetime] = None


class EnrollmentWindow(SQLModel, table=True):
    """Singleton row id='default' — admin opens briefly so parents can enroll without typing a key."""

    __tablename__ = "enrollment_window"

    id: str = Field(default="default", primary_key=True, max_length=32)
    enabled: bool = False
    expires_at: Optional[datetime] = None


class AppScanResult(SQLModel, table=True):
    __tablename__ = "app_scan_result"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    device_uuid: str = Field(index=True)
    package_name: str
    installer: Optional[str] = None
    dangerous_permissions: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    risk_score: int = 0
    reasons: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]")
    )
    created_at: datetime = Field(default_factory=_utcnow)


class DeviceHealthEvent(SQLModel, table=True):
    __tablename__ = "device_health_event"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    device_uuid: str = Field(index=True, max_length=128)
    type: str = Field(max_length=64)
    detail: Optional[str] = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=_utcnow)


class AppAllowlist(SQLModel, table=True):
    __tablename__ = "app_allowlist"

    package_name: str = Field(primary_key=True, max_length=256)
    note: Optional[str] = Field(default=None, max_length=512)
    created_at: datetime = Field(default_factory=_utcnow)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    actor: str = Field(default="admin", max_length=64)
    action: str = Field(max_length=64)
    resource_type: str = Field(max_length=64)
    resource_id: Optional[str] = Field(default=None, max_length=128)
    detail: Optional[str] = Field(default=None, max_length=1024)
    created_at: datetime = Field(default_factory=_utcnow)
