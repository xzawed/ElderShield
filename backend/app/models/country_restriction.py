"""Country restriction group and its immutable version snapshots."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CountryRestriction(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    countries: list[str] = Field(sa_column=Column(JSON, nullable=False))
    apply_to: list[str] = Field(sa_column=Column(JSON, nullable=False))
    enabled: bool = True
    version: int = 1
    description: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class CountryRestrictionVersion(SQLModel, table=True):
    """Point-in-time copy used by rollback. Live row version keeps moving forward."""

    restriction_id: str = Field(primary_key=True)
    version: int = Field(primary_key=True)
    name: str
    countries: list[str] = Field(sa_column=Column(JSON, nullable=False))
    apply_to: list[str] = Field(sa_column=Column(JSON, nullable=False))
    enabled: bool
