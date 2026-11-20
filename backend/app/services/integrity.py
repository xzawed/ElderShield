"""Play Integrity verification for device enroll.

Production: fail closed unless skip flag or Google decode confirms MEETS_DEVICE_INTEGRITY
and (when provided) requestDetails.nonce matches the client nonce.
Lab/pytest: ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core import config as config_module

logger = logging.getLogger(__name__)


def verify_integrity_token(
    integrity_token: str | None,
    *,
    expected_nonce: str | None = None,
) -> bool:
    if config_module.settings.enroll_skip_integrity:
        return True
    if not integrity_token:
        return False
    return _google_play_integrity_ok(integrity_token, expected_nonce=expected_nonce)


def _google_play_integrity_ok(
    integrity_token: str,
    *,
    expected_nonce: str | None,
) -> bool:
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
    if not _meets_device_integrity(payload):
        return False
    if not _package_matches(payload, package):
        return False
    if expected_nonce and not _nonce_matches(payload, expected_nonce):
        logger.warning("Play Integrity nonce mismatch")
        return False
    return True


def _decode_integrity_token(integrity_token: str, package_name: str) -> dict[str, Any]:
    """Call Google Play Integrity decodeIntegrityToken."""
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


def _package_matches(payload: dict[str, Any], package_name: str) -> bool:
    details = payload.get("requestDetails") or payload.get("request_details") or {}
    reported = details.get("requestPackageName") or details.get("request_package_name")
    if not reported:
        # Some lab/stub payloads omit requestDetails — require when present.
        return True
    return reported == package_name


def _nonce_matches(payload: dict[str, Any], expected_nonce: str) -> bool:
    details = payload.get("requestDetails") or payload.get("request_details") or {}
    reported = details.get("nonce")
    return isinstance(reported, str) and reported == expected_nonce
