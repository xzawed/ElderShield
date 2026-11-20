"""Best-effort admin notifications (Phase 2A). Never raises to API callers."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)


def notify_admin(text: str) -> bool:
    url = (settings.admin_notify_webhook_url or "").strip()
    if not url:
        return False
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("admin_notify failed: %s", exc)
        return False
