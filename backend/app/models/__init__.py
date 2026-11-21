"""Importing this package registers SQLModel tables on SQLModel.metadata."""

from app.models.call_rule import CallRule
from app.models.country_restriction import CountryRestriction, CountryRestrictionVersion
from app.models.device import (
    AppAllowlist,
    AppScanResult,
    AuditLog,
    Device,
    DeviceHealthEvent,
    EnrollmentWindow,
    UsedIntegrityToken,
)
from app.models.incident import Incident
from app.models.rule_bundle_meta import RuleBundleMeta

__all__ = [
    "CountryRestriction",
    "CountryRestrictionVersion",
    "CallRule",
    "Device",
    "AppScanResult",
    "DeviceHealthEvent",
    "AppAllowlist",
    "AuditLog",
    "EnrollmentWindow",
    "UsedIntegrityToken",
    "Incident",
    "RuleBundleMeta",
]
