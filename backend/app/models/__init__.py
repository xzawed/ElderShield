"""Importing this package registers SQLModel tables on SQLModel.metadata."""

from app.models.country_restriction import CountryRestriction, CountryRestrictionVersion
from app.models.device import AppScanResult, Device

__all__ = [
    "CountryRestriction",
    "CountryRestrictionVersion",
    "Device",
    "AppScanResult",
]
