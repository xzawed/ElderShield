from collections.abc import Generator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401 — register tables on SQLModel.metadata
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def _sqlite_add_column_if_missing(table: str, column: str, ddl_type: str) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        names = {r[1] for r in rows}
        if column not in names:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    # Lab DBs created before coexistence fields — additive only.
    _sqlite_add_column_if_missing("device", "call_screening_held_by", "VARCHAR(256)")
    _sqlite_add_column_if_missing("device", "call_screening_peers", "JSON DEFAULT '[]'")


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
