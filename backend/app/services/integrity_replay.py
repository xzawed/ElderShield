"""Reject reused integrity tokens at enroll."""

from __future__ import annotations

from sqlmodel import Session

from app.models.device import UsedIntegrityToken
from app.services.device_tokens import hash_device_token


def consume_integrity_token(session: Session, integrity_token: str | None) -> bool:
    """Return True if token is new and recorded; False if replay.

    Empty/None tokens are not recorded (caller must already reject when skip is off).
    """
    if not integrity_token:
        return True
    digest = hash_device_token(integrity_token)
    if session.get(UsedIntegrityToken, digest) is not None:
        return False
    session.add(UsedIntegrityToken(token_hash=digest))
    session.commit()
    return True
