from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.models.country_restriction import CountryRestriction


def build_rule_bundle(session: Session) -> dict[str, Any]:
    rows = list(session.exec(select(CountryRestriction)).all())
    version = max((r.version for r in rows), default=0)
    return {
        "version": version,
        "countryRestrictions": [
            {
                "id": r.id,
                "name": r.name,
                "countries": list(r.countries),
                "applyTo": list(r.apply_to),
                "enabled": r.enabled,
                "version": r.version,
                "description": r.description,
            }
            for r in rows
        ],
        "callRules": [],
        "appRiskRules": [],
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
