"""CallRule — whitelist / country-code helpers for CallScreening."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CallRule(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    country_codes: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    whitelist: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    enabled: bool = True
    version: int = 1
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
