"""Create CallRules and bump RuleBundle generation."""

from datetime import datetime, timezone

from sqlmodel import Session

from app.models.call_rule import CallRule
from app.services.bundle_version import bump_bundle_version


def create_call_rule(
    session: Session,
    *,
    country_codes: list[str] | None = None,
    whitelist: list[str] | None = None,
    enabled: bool = True,
) -> CallRule:
    codes = list(country_codes or [])
    wl = list(whitelist or [])
    if not isinstance(codes, list) or not isinstance(wl, list):
        raise TypeError("country_codes and whitelist must be lists")
    now = datetime.now(timezone.utc)
    row = CallRule(
        country_codes=codes,
        whitelist=wl,
        enabled=enabled,
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    bump_bundle_version(session)
    session.commit()
    session.refresh(row)
    return row
