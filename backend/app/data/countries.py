"""ISO 3166-1 alpha-2 country master for admin multi-select and API."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA = Path(__file__).with_name("country_master.json")


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, Any], ...]:
    raw = json.loads(_DATA.read_text(encoding="utf-8"))
    return tuple(raw)


def country_master() -> list[dict[str, Any]]:
    """List of {code, name_en, name_ko, calling_code, name} where name defaults to name_en."""
    rows: list[dict[str, Any]] = []
    for row in _load():
        item = dict(row)
        item.setdefault("name", item.get("name_en") or item["code"])
        rows.append(item)
    return rows


def country_label(row: dict[str, Any], lang: str) -> str:
    if lang == "ko":
        return str(row.get("name_ko") or row.get("name_en") or row["code"])
    return str(row.get("name_en") or row.get("name") or row["code"])


# Backward-compatible module attribute (list of dicts with name=en).
COUNTRY_MASTER: list[dict[str, Any]] = country_master()
