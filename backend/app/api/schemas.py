from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
    calling_code: str = Field(serialization_alias="callingCode", validation_alias="callingCode")


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
