"""Admin-controlled enrollment window (parents install without typing a key)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.core import config as config_module
from app.models.device import EnrollmentWindow

DEFAULT_WINDOW_ID = "default"
DEFAULT_TTL_MINUTES = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_enrollment_window(session: Session) -> EnrollmentWindow:
    row = session.get(EnrollmentWindow, DEFAULT_WINDOW_ID)
    if row is None:
        row = EnrollmentWindow(
            id=DEFAULT_WINDOW_ID,
            enabled=False,
            expires_at=None,
            enroll_count=0,
            max_enrolls=config_module.settings.enroll_max_per_window,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
    return row


def is_enrollment_open(session: Session) -> bool:
    row = get_enrollment_window(session)
    if not row.enabled:
        return False
    if row.expires_at is None:
        return False
    exp = row.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > _utcnow()


def open_enrollment(session: Session, *, minutes: int = DEFAULT_TTL_MINUTES) -> EnrollmentWindow:
    row = get_enrollment_window(session)
    row.enabled = True
    row.expires_at = _utcnow() + timedelta(minutes=max(1, minutes))
    row.enroll_count = 0
    row.max_enrolls = max(1, config_module.settings.enroll_max_per_window)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def close_enrollment(session: Session) -> EnrollmentWindow:
    row = get_enrollment_window(session)
    row.enabled = False
    row.expires_at = None
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def remaining_enrolls(session: Session) -> int:
    row = get_enrollment_window(session)
    return max(0, int(row.max_enrolls) - int(row.enroll_count))


def record_enroll(session: Session) -> EnrollmentWindow:
    row = get_enrollment_window(session)
    row.enroll_count = int(row.enroll_count) + 1
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
