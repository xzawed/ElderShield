"""UT-B-01..06 — CountryRestriction version & countries invariants (TDD)."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Domain under test (implemented in S1.2)
from app.models.country_restriction import CountryRestriction
from app.services.country_restriction_service import (
    create_country_restriction,
    update_country_restriction,
)


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_ut_b_01_create_starts_at_version_1_and_countries_list(session: Session) -> None:
    row = create_country_restriction(
        session,
        name="고위험",
        countries=["CN", "RU"],
        apply_to=["call", "dns"],
        enabled=True,
        description="test",
    )
    assert row.version == 1
    assert isinstance(row.countries, list)
    assert row.countries == ["CN", "RU"]


def test_ut_b_02_put_countries_increments_version(session: Session) -> None:
    row = create_country_restriction(
        session,
        name="고위험",
        countries=["CN"],
        apply_to=["call"],
        enabled=True,
    )
    updated = update_country_restriction(session, row.id, countries=["CN", "RU"])
    assert updated is not None
    assert updated.version == 2
    assert updated.countries == ["CN", "RU"]


def test_ut_b_03_enabled_toggle_increments_version(session: Session) -> None:
    row = create_country_restriction(
        session,
        name="고위험",
        countries=["CN"],
        apply_to=["call"],
        enabled=True,
    )
    updated = update_country_restriction(session, row.id, enabled=False)
    assert updated is not None
    assert updated.enabled is False
    assert updated.version == 2


def test_ut_b_04_countries_must_be_list_not_string(session: Session) -> None:
    with pytest.raises((TypeError, ValueError)):
        create_country_restriction(
            session,
            name="bad",
            countries="CN",  # type: ignore[arg-type]
            apply_to=["call"],
            enabled=True,
        )


def test_ut_b_05_empty_countries_when_enabled_rejected(session: Session) -> None:
    with pytest.raises(ValueError):
        create_country_restriction(
            session,
            name="empty",
            countries=[],
            apply_to=["call"],
            enabled=True,
        )


def test_ut_b_06_rollback_publishes_new_version(session: Session) -> None:
    from app.services.rule_bundle_service import publish_rollback

    row = create_country_restriction(
        session,
        name="고위험",
        countries=["CN"],
        apply_to=["call"],
        enabled=True,
    )
    update_country_restriction(session, row.id, countries=["CN", "RU"])
    # Snapshot at version 1 content, publish as new bundle version
    result = publish_rollback(session, target_restriction_version=1, restriction_id=row.id)
    assert result["restriction"].countries == ["CN"]
    assert result["restriction"].version == 3  # new version, history preserved
    assert result["bundle_version"] >= 1
