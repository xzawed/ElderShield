"""Per-device API tokens — store only SHA-256 hashes server-side."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_device_token() -> str:
    return secrets.token_urlsafe(32)


def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_device_token(token), token_hash)
