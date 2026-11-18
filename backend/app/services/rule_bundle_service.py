"""Publish a historical country-restriction snapshot as a new version."""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.country_restriction import CountryRestriction, CountryRestrictionVersion
from app.services.country_restriction_service import save_version_snapshot


def publish_rollback(
    session: Session,
    target_restriction_version: int,
    restriction_id: str,
) -> dict[str, object]:
    row = session.get(CountryRestriction, restriction_id)
    if row is None:
        raise ValueError(f"country restriction not found: {restriction_id}")

    snap = session.exec(
        select(CountryRestrictionVersion).where(
            CountryRestrictionVersion.restriction_id == restriction_id,
            CountryRestrictionVersion.version == target_restriction_version,
        )
    ).first()
    if snap is None:
        raise ValueError(
            f"no snapshot for restriction {restriction_id} version {target_restriction_version}"
        )

    row.name = snap.name
    row.countries = list(snap.countries)
    row.apply_to = list(snap.apply_to) if isinstance(snap.apply_to, list) else snap.apply_to
    row.enabled = snap.enabled
    row.version = row.version + 1
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    save_version_snapshot(session, row)
    session.commit()
    session.refresh(row)

    bundle_version = session.exec(select(func.max(CountryRestriction.version))).one()
    return {"restriction": row, "bundle_version": int(bundle_version or 0)}
