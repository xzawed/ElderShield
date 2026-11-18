"""Importing this package registers SQLModel tables on SQLModel.metadata."""

from app.models.country_restriction import CountryRestriction, CountryRestrictionVersion

__all__ = ["CountryRestriction", "CountryRestrictionVersion"]
