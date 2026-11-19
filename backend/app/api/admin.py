from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session, select

from app.api.deps import require_admin
from app.api.schemas import (
    CallRuleCreate,
    CallRuleOut,
    CountryMasterOut,
    CountryRestrictionCreate,
    CountryRestrictionOut,
    CountryRestrictionUpdate,
    RulesRollbackOut,
    RulesRollbackRequest,
)
from app.data.countries import COUNTRY_MASTER
from app.db import get_session
from app.models.call_rule import CallRule
from app.models.country_restriction import CountryRestriction
from app.models.device import AppScanResult
from app.services.call_rule_service import create_call_rule
from app.services.country_restriction_service import (
    create_country_restriction,
    delete_country_restriction,
    update_country_restriction,
)
from app.services.rule_bundle_service import publish_rollback

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
    if not delete_country_restriction(session, restriction_id):
        raise HTTPException(status_code=404, detail="Not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/call-rules", response_model=list[CallRuleOut])
def list_call_rules(session: Session = Depends(get_session)) -> list[CallRule]:
    return list(session.exec(select(CallRule)).all())


@router.post("/call-rules", response_model=CallRuleOut, status_code=status.HTTP_201_CREATED)
def post_call_rule(
    body: CallRuleCreate, session: Session = Depends(get_session)
) -> CallRule:
    try:
        return create_call_rule(
            session,
            country_codes=body.country_codes,
            whitelist=body.whitelist,
            enabled=body.enabled,
        )
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/rules/rollback", response_model=RulesRollbackOut)
def rollback_rules(
    body: RulesRollbackRequest, session: Session = Depends(get_session)
) -> RulesRollbackOut:
    try:
        result = publish_rollback(
            session,
            target_restriction_version=body.target_version,
            restriction_id=body.restriction_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    row = result["restriction"]
    assert isinstance(row, CountryRestriction)
    return RulesRollbackOut(
        id=row.id,
        name=row.name,
        countries=list(row.countries),
        apply_to=list(row.apply_to),
        enabled=row.enabled,
        version=row.version,
        description=row.description,
        bundle_version=int(result["bundle_version"]),
    )


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
