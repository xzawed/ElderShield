"""Startup must refuse insecure / colliding API keys unless explicitly allowed."""

import pytest

from app.core.config import Settings, assert_secure_settings


def test_rejects_insecure_default_keys(monkeypatch) -> None:
    monkeypatch.delenv("ELDERSHIELD_ALLOW_INSECURE_DEFAULTS", raising=False)
    s = Settings(
        database_url="sqlite://",
        admin_api_key="change-me-admin",
        device_api_key="change-me-device",
    )
    with pytest.raises(RuntimeError, match="insecure"):
        assert_secure_settings(s)


def test_rejects_identical_admin_and_device_keys(monkeypatch) -> None:
    monkeypatch.delenv("ELDERSHIELD_ALLOW_INSECURE_DEFAULTS", raising=False)
    s = Settings(
        database_url="sqlite://",
        admin_api_key="same-secret",
        device_api_key="same-secret",
    )
    with pytest.raises(RuntimeError, match="must differ"):
        assert_secure_settings(s)


def test_accepts_distinct_non_default_keys(monkeypatch) -> None:
    monkeypatch.delenv("ELDERSHIELD_ALLOW_INSECURE_DEFAULTS", raising=False)
    s = Settings(
        database_url="sqlite://",
        admin_api_key="test-admin-key",
        device_api_key="test-device-key",
    )
    assert_secure_settings(s)


def test_allow_insecure_flag_skips_check() -> None:
    s = Settings(
        database_url="sqlite://",
        admin_api_key="change-me-admin",
        device_api_key="change-me-device",
    )
    assert_secure_settings(s, allow_insecure=True)
