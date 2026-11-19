"""Create and update country restrictions with monotonic versions."""

from datetime import datetime, timezone

from sqlmodel import Session

from app.models.country_restriction import CountryRestriction, CountryRestrictionVersion
from app.services.bundle_version import bump_bundle_version

_MUTABLE = {"name", "countries", "apply_to", "enabled", "description"}


def _as_country_list(countries: object) -> list[str]:
    if isinstance(countries, str) or not isinstance(countries, list):
        raise TypeError("countries must be a list")
    return list(countries)


def _reject_empty_enabled(countries: list[str], enabled: bool) -> None:
    if enabled and len(countries) == 0:
        raise ValueError("enabled country restriction requires a non-empty countries list")


def _snapshot(row: CountryRestriction) -> CountryRestrictionVersion:
    apply_to = row.apply_to
    return CountryRestrictionVersion(
        restriction_id=row.id,
        version=row.version,
        name=row.name,
        countries=list(row.countries),
        apply_to=list(apply_to) if isinstance(apply_to, list) else apply_to,
        enabled=row.enabled,
    )


def save_version_snapshot(session: Session, row: CountryRestriction) -> None:
    session.add(_snapshot(row))


def create_country_restriction(
    session: Session,
    name: str,
    countries: list[str],
    apply_to: list[str],
    enabled: bool,
    description: str | None = None,
) -> CountryRestriction:
    countries = _as_country_list(countries)
    if not isinstance(apply_to, list):
        raise TypeError("apply_to must be a list")
    _reject_empty_enabled(countries, enabled)
    now = datetime.now(timezone.utc)
    row = CountryRestriction(
        name=name,
        countries=countries,
        apply_to=list(apply_to),
        enabled=enabled,
        version=1,
        description=description,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    save_version_snapshot(session, row)
    bump_bundle_version(session)
    session.commit()
    session.refresh(row)
    return row


def update_country_restriction(
    session: Session,
    id: str,
    **fields: object,
) -> CountryRestriction | None:
    row = session.get(CountryRestriction, id)
    if row is None:
        return None

    countries = (
        _as_country_list(fields["countries"]) if "countries" in fields else list(row.countries)
    )
    enabled = fields["enabled"] if "enabled" in fields else row.enabled
    _reject_empty_enabled(countries, bool(enabled))

    fields.pop("version", None)
    if "countries" in fields:
        fields["countries"] = countries
    for key, value in fields.items():
        if key in _MUTABLE:
            setattr(row, key, value)
    row.version += 1
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    save_version_snapshot(session, row)
    bump_bundle_version(session)
    session.commit()
    session.refresh(row)
    return row


def delete_country_restriction(session: Session, id: str) -> bool:
    row = session.get(CountryRestriction, id)
    if row is None:
        return False
    session.delete(row)
    bump_bundle_version(session)
    session.commit()
    return True
