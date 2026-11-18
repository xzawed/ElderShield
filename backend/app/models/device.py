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
    last_rule_version: int = 0
    last_sync_at: Optional[datetime] = None


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
    created_at: datetime = Field(default_factory=_utcnow)
