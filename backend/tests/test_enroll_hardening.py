import pytest

ADMIN = {"X-API-Key": "test-admin-key"}


def _open(client, **extra):
    body = {"enabled": True, "ttlMinutes": 30}
    body.update(extra)
    assert client.post("/api/v1/admin/enrollment-window", headers=ADMIN, json=body).status_code == 200


def test_integrity_token_replay_rejected(client):
    _open(client)
    first = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": "replay-me-once", "appVersion": "0.2.0"},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": "replay-me-once", "appVersion": "0.2.0"},
    )
    assert second.status_code == 403
    assert second.json()["detail"] == "integrity_replay"


def test_enroll_max_per_window(client, monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(
        config_module,
        "settings",
        config_module.Settings(
            database_url="sqlite://",
            admin_api_key="test-admin-key",
            device_api_key="test-device-key",
            enroll_skip_integrity=True,
            enroll_max_per_window=2,
            enroll_rate_limit_per_minute=100,
        ),
    )
    _open(client)
    assert (
        client.post(
            "/api/v1/devices/enroll",
            json={"integrityToken": "cap-1", "appVersion": "0.2.0"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/devices/enroll",
            json={"integrityToken": "cap-2", "appVersion": "0.2.0"},
        ).status_code
        == 201
    )
    third = client.post(
        "/api/v1/devices/enroll",
        json={"integrityToken": "cap-3", "appVersion": "0.2.0"},
    )
    assert third.status_code == 403
    assert third.json()["detail"] == "enrollment_cap"


def test_enroll_skip_integrity_refused_without_allow_insecure(monkeypatch):
    from app.core.config import Settings, assert_secure_settings

    monkeypatch.delenv("ELDERSHIELD_ALLOW_INSECURE_DEFAULTS", raising=False)
    s = Settings(
        database_url="sqlite://",
        admin_api_key="strong-admin-key-xxx",
        device_api_key="strong-device-key-yyy",
        enroll_skip_integrity=True,
    )
    with pytest.raises(RuntimeError, match="ENROLL_SKIP_INTEGRITY"):
        assert_secure_settings(s, allow_insecure=False)
