from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from app.models.call_rule import CallRule
from app.models.country_restriction import CountryRestriction
from app.services.bundle_version import get_bundle_version


def build_rule_bundle(session: Session) -> dict[str, Any]:
    rows = list(session.exec(select(CountryRestriction)).all())
    call_rows = list(session.exec(select(CallRule)).all())
    version = get_bundle_version(session)
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
        "callRules": [
            {
                "id": c.id,
                "countryCodes": list(c.country_codes),
                "whitelist": list(c.whitelist),
                "enabled": c.enabled,
                "version": c.version,
            }
            for c in call_rows
        ],
        "appRiskRules": [],
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
