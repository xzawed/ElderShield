"""Play Integrity verification for device enroll.

Production: fail closed unless skip flag or Google decode confirms MEETS_DEVICE_INTEGRITY.
Lab/pytest: ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core import config as config_module

logger = logging.getLogger(__name__)


def verify_integrity_token(integrity_token: str | None) -> bool:
    if config_module.settings.enroll_skip_integrity:
        return True
    if not integrity_token:
        return False
    return _google_play_integrity_ok(integrity_token)


def _google_play_integrity_ok(integrity_token: str) -> bool:
    """Decode via Play Integrity API when enabled; otherwise fail closed."""
    if not config_module.settings.play_integrity_enabled:
        logger.warning("Play Integrity path requested but PLAY_INTEGRITY_ENABLED!=1")
        return False
    package = (config_module.settings.play_package_name or "").strip()
    if not package:
        logger.warning("PLAY_PACKAGE_NAME unset — cannot decode Integrity token")
        return False
    try:
        payload = _decode_integrity_token(integrity_token, package)
    except Exception:
        logger.exception("Play Integrity decode failed")
        return False
    return _meets_device_integrity(payload)


def _decode_integrity_token(integrity_token: str, package_name: str) -> dict[str, Any]:
    """Call Google Play Integrity decodeIntegrityToken.

    Requires Application Default Credentials (e.g. GOOGLE_APPLICATION_CREDENTIALS)
    with Play Integrity API access for the Cloud project linked to the Play app.
    Optional dependency: google-api-python-client, google-auth.
    """
    try:
        from google.auth import default as google_auth_default
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "google-api-python-client and google-auth required for Play Integrity decode"
        ) from exc

    credentials, _ = google_auth_default(
        scopes=["https://www.googleapis.com/auth/playintegrity"]
    )
    service = build("playintegrity", "v1", credentials=credentials, cache_discovery=False)
    request_body = {"integrityToken": integrity_token}
    response = (
        service.v1()
        .decodeIntegrityToken(packageName=package_name, body=request_body)
        .execute()
    )
    external = response.get("tokenPayloadExternal") or response.get("token_payload_external") or {}
    if not isinstance(external, dict):
        return {}
    return external


def _meets_device_integrity(payload: dict[str, Any]) -> bool:
    device = payload.get("deviceIntegrity") or payload.get("device_integrity") or {}
    verdicts = (
        device.get("deviceRecognitionVerdict")
        or device.get("device_recognition_verdict")
        or []
    )
    if isinstance(verdicts, str):
        verdicts = [verdicts]
    return "MEETS_DEVICE_INTEGRITY" in verdicts
