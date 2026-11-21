from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CountryRestrictionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    countries: list[str]
    apply_to: list[str] = Field(alias="applyTo")
    enabled: bool = True
    description: Optional[str] = None


class CountryRestrictionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    countries: Optional[list[str]] = None
    apply_to: Optional[list[str]] = Field(default=None, alias="applyTo")
    enabled: Optional[bool] = None
    description: Optional[str] = None


class CountryRestrictionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, ser_json_by_alias=True)

    id: str
    name: str
    countries: list[str]
    apply_to: list[str] = Field(serialization_alias="applyTo", validation_alias="applyTo")
    enabled: bool
    version: int
    description: Optional[str] = None


class CountryMasterOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    code: str
    name: str
    name_en: str = Field(serialization_alias="nameEn", validation_alias="nameEn")
    name_ko: str = Field(serialization_alias="nameKo", validation_alias="nameKo")
    calling_code: str = Field(serialization_alias="callingCode", validation_alias="callingCode")


class DnsDenylistOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    source: str
    countries: list[str]
    tlds: list[str] = Field(default_factory=list)
    domains: list[str]
    threat_hosts: list[str] = Field(
        default_factory=list,
        serialization_alias="threatHosts",
        validation_alias=AliasChoices("threatHosts", "threat_hosts"),
    )
    threat_hosts_lab: list[str] = Field(
        default_factory=list,
        serialization_alias="threatHostsLab",
        validation_alias=AliasChoices("threatHostsLab", "threat_hosts_lab"),
    )
    count: int


class NextDnsSyncOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    ok: bool
    profile_id: str = Field(serialization_alias="profileId", validation_alias="profileId")
    plan: DnsDenylistOut
    tlds: dict
    denylist: dict


class CallRuleCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    country_codes: list[str] = Field(default_factory=list, alias="countryCodes")
    whitelist: list[str] = Field(default_factory=list)
    enabled: bool = True


class CallRuleOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, ser_json_by_alias=True)

    id: str
    country_codes: list[str] = Field(serialization_alias="countryCodes")
    whitelist: list[str]
    enabled: bool
    version: int


class DeviceOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, ser_json_by_alias=True)

    device_uuid: str = Field(serialization_alias="deviceUuid")
    name: Optional[str] = None
    model: Optional[str] = None
    app_version: str = Field(serialization_alias="appVersion")
    dns_configured: bool = Field(serialization_alias="dnsConfigured")
    call_screening_enabled: bool = Field(serialization_alias="callScreeningEnabled")
    call_screening_held_by: Optional[str] = Field(
        default=None, serialization_alias="callScreeningHeldBy"
    )
    call_screening_peers: list[str] = Field(
        default_factory=list, serialization_alias="callScreeningPeers"
    )
    last_rule_version: int = Field(serialization_alias="lastRuleVersion")
    last_sync_at: Optional[datetime] = Field(default=None, serialization_alias="lastSyncAt")
    dns_host_class: Optional[str] = Field(default=None, serialization_alias="dnsHostClass")
    last_sync_ok: bool = Field(default=True, serialization_alias="lastSyncOk")
    last_sync_error_code: Optional[str] = Field(
        default=None, serialization_alias="lastSyncErrorCode"
    )
    cached_bundle_version: int = Field(default=0, serialization_alias="cachedBundleVersion")
    protection_degraded: bool = Field(default=False, serialization_alias="protectionDegraded")


class RulesRollbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    restriction_id: str = Field(alias="restrictionId")
    target_version: int = Field(alias="targetVersion")


class RulesRollbackOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, ser_json_by_alias=True)

    id: str
    name: str
    countries: list[str]
    apply_to: list[str] = Field(serialization_alias="applyTo")
    enabled: bool
    version: int
    description: Optional[str] = None
    bundle_version: int = Field(serialization_alias="bundleVersion")


class IncidentIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    incident_id: str = Field(alias="incidentId")
    device_uuid: str = Field(alias="deviceUuid")
    triggered_at: datetime = Field(alias="triggeredAt")
    triggers: list[str]
    window: Optional[dict] = None
    apps: list[dict] = Field(default_factory=list)
    calls: list[dict] = Field(default_factory=list)
    dns: dict = Field(default_factory=dict)
    country_hints: Optional[dict] = Field(default=None, alias="countryHints")
    protection_snapshot: Optional[dict] = Field(default=None, alias="protectionSnapshot")


class IncidentOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True, ser_json_by_alias=True)

    incident_id: str = Field(
        serialization_alias="incidentId",
        validation_alias=AliasChoices("incidentId", "incident_id"),
    )
    device_uuid: str = Field(
        serialization_alias="deviceUuid",
        validation_alias=AliasChoices("deviceUuid", "device_uuid"),
    )
    triggered_at: datetime = Field(
        serialization_alias="triggeredAt",
        validation_alias=AliasChoices("triggeredAt", "triggered_at"),
    )
    triggers: list[str]
    payload: dict
    created_at: datetime = Field(
        serialization_alias="createdAt",
        validation_alias=AliasChoices("createdAt", "created_at"),
    )

    @classmethod
    def from_row(cls, row: object) -> "IncidentOut":
        payload = getattr(row, "payload", None) or {}
        if not isinstance(payload, dict):
            payload = {}
        return cls(
            incident_id=getattr(row, "id"),
            device_uuid=getattr(row, "device_uuid"),
            triggered_at=getattr(row, "triggered_at"),
            triggers=list(getattr(row, "triggers", None) or []),
            payload=payload,
            created_at=getattr(row, "created_at"),
        )
