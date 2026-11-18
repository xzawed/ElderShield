from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.api.deps import require_admin
from app.api.schemas import (
    CountryMasterOut,
    CountryRestrictionCreate,
    CountryRestrictionOut,
    CountryRestrictionUpdate,
)
from app.data.countries import COUNTRY_MASTER
from app.db import get_session
from app.models.country_restriction import CountryRestriction
from app.models.device import AppScanResult
from app.services.country_restriction_service import (
    create_country_restriction,
    update_country_restriction,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/countries", response_model=list[CountryMasterOut])
def list_countries() -> list[CountryMasterOut]:
    return [
        CountryMasterOut(code=c["code"], name=c["name"], callingCode=c["calling_code"])
        for c in COUNTRY_MASTER
    ]


@router.get("/country-restrictions", response_model=list[CountryRestrictionOut])
def list_restrictions(session: Session = Depends(get_session)) -> list[CountryRestriction]:
    return list(session.exec(select(CountryRestriction)).all())


@router.post(
    "/country-restrictions",
    response_model=CountryRestrictionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_restriction(
    body: CountryRestrictionCreate, session: Session = Depends(get_session)
) -> CountryRestriction:
    try:
        return create_country_restriction(
            session,
            name=body.name,
            countries=body.countries,
            apply_to=body.apply_to,
            enabled=body.enabled,
            description=body.description,
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/country-restrictions/{restriction_id}", response_model=CountryRestrictionOut)
def put_restriction(
    restriction_id: str,
    body: CountryRestrictionUpdate,
    session: Session = Depends(get_session),
) -> CountryRestriction:
    patch = body.model_dump(exclude_unset=True, by_alias=False)
    if "apply_to" not in patch and "applyTo" in body.model_dump(exclude_unset=True, by_alias=True):
        patch["apply_to"] = body.apply_to
    try:
        updated = update_country_restriction(session, restriction_id, **patch)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Not found")
    return updated


@router.delete("/country-restrictions/{restriction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_restriction(
    restriction_id: str, session: Session = Depends(get_session)
) -> Response:
    row = session.get(CountryRestriction, restriction_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(row)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/devices/{device_uuid}/scan-results")
def list_scan_results(device_uuid: str, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(
        select(AppScanResult).where(AppScanResult.device_uuid == device_uuid)
    ).all()
    return [
        {
            "packageName": r.package_name,
            "installer": r.installer,
            "dangerousPermissions": list(r.dangerous_permissions),
            "riskScore": r.risk_score,
        }
        for r in rows
    ]
