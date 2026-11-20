from __future__ import annotations

from sqlmodel import Session

from app.models.device import AuditLog


def record_audit(
    session: Session,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    actor: str = "admin",
    commit: bool = False,
) -> AuditLog:
    row = AuditLog(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
    )
    session.add(row)
    if commit:
        session.commit()
        session.refresh(row)
    return row
