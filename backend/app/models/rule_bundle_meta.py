"""Monotonic RuleBundle generation counter (sync key for devices)."""

from sqlmodel import Field, SQLModel

SINGLETON_ID = "latest"


class RuleBundleMeta(SQLModel, table=True):
    """Single-row table: version rises on every restriction create/update/delete/rollback."""

    id: str = Field(default=SINGLETON_ID, primary_key=True)
    version: int = 0
