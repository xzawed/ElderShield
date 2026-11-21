from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(SQLModel, table=True):
    __tablename__ = "incident"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    device_uuid: str = Field(index=True, max_length=128)
    triggered_at: datetime = Field(index=True)
    triggers: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=_utcnow)
