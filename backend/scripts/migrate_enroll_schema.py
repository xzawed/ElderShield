"""Apply additive SQLite columns + create enrollment_window. Safe to re-run."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.db import engine, init_db


def main() -> None:
    init_db()
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(device)")).fetchall()]
        tables = [
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        ]
    print("api_token_hash", "api_token_hash" in cols)
    print("token_revoked_at", "token_revoked_at" in cols)
    print("enrollment_window", "enrollment_window" in tables)


if __name__ == "__main__":
    main()
