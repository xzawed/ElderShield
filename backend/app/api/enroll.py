from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.db import get_session
from app.models.device import Device
from app.services.admin_notify import notify_admin
from app.services.device_tokens import generate_device_token, hash_device_token
from app.services.enroll_rate_limit import allow_enroll
from app.services.enrollment_window import (
    is_enrollment_open,
    record_enroll,
    remaining_enrolls,
)
from app.services.integrity import verify_integrity_token
from app.services.integrity_replay import consume_integrity_token

router = APIRouter(prefix="/api/v1", tags=["enroll"])


class EnrollIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    integrity_token: str | None = Field(default=None, alias="integrityToken")
    app_version: str = Field(default="0.0.0", alias="appVersion")
    model: str | None = Field(default=None, alias="model")


class EnrollOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    device_uuid: str = Field(serialization_alias="deviceUuid")
    device_token: str = Field(serialization_alias="deviceToken")


@router.post("/devices/enroll", response_model=EnrollOut, status_code=status.HTTP_201_CREATED)
def enroll_device(
    body: EnrollIn,
    request: Request,
    session: Session = Depends(get_session),
) -> EnrollOut:
    client = request.client.host if request.client else "unknown"
    if not allow_enroll(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="enroll_rate_limited",
        )
    if not is_enrollment_open(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="enrollment_closed",
        )
    if remaining_enrolls(session) <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="enrollment_cap",
        )
    if not verify_integrity_token(body.integrity_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="integrity_failed",
        )
    if not consume_integrity_token(session, body.integrity_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="integrity_replay",
        )

    token = generate_device_token()
    device_uuid = str(uuid4())
    device = Device(
        device_uuid=device_uuid,
        model=body.model,
        app_version=body.app_version,
        api_token_hash=hash_device_token(token),
        last_sync_at=datetime.now(timezone.utc),
    )
    session.add(device)
    session.commit()
    record_enroll(session)

    notify_admin(f"device_enrolled deviceUuid={device_uuid} model={body.model or '-'}")
    return EnrollOut(device_uuid=device_uuid, device_token=token)
