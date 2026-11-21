"""Pull blocked DNS queries from NextDNS logs for incident axis C.

Official API (https://nextdns.github.io/api/):
- GET /profiles/:id/logs  query: from, to, status=blocked, limit, cursor, sort
Response items use timestamp + domain + status.

Never raises to API callers: missing env or HTTP failure → [].
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.nextdns_sync import API_BASE, _headers

logger = logging.getLogger(__name__)

_MAX_PAGES = 10
_PAGE_LIMIT = 1000
_TIMEOUT_SEC = 30.0


def _credentials() -> tuple[str, str] | None:
    api_key = (os.environ.get("NEXTDNS_API_KEY") or "").strip()
    profile_id = (os.environ.get("NEXTDNS_PROFILE_ID") or "").strip()
    if not api_key or not profile_id:
        return None
    return api_key, profile_id


def nextdns_configured() -> bool:
    return _credentials() is not None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return _as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        return _as_utc(datetime.fromisoformat(raw))
    except ValueError:
        return None


def _window_bounds(payload: dict) -> tuple[datetime, datetime] | None:
    window = payload.get("window") if isinstance(payload.get("window"), dict) else {}
    from_ts = _parse_dt(window.get("from"))
    to_ts = _parse_dt(window.get("to"))
    if from_ts is None or to_ts is None:
        return None
    return from_ts, to_ts


def _map_log_entry(item: dict) -> dict[str, str] | None:
    status = str(item.get("status") or "").lower()
    if status and status != "blocked":
        return None
    domain = str(item.get("domain") or "").strip()
    if not domain:
        return None
    at = item.get("timestamp") or item.get("at") or ""
    return {"at": str(at), "domain": domain, "action": "block"}


def _merge_dns_events(existing: list, incoming: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for ev in list(existing or []) + list(incoming or []):
        if not isinstance(ev, dict):
            continue
        key = (str(ev.get("at") or ""), str(ev.get("domain") or ""))
        if key in seen:
            continue
        seen.add(key)
        mapped = {
            "at": str(ev.get("at") or ""),
            "domain": str(ev.get("domain") or ""),
            "action": str(ev.get("action") or "block"),
        }
        if mapped["domain"]:
            out.append(mapped)
    return out


def fetch_blocked_domains(
    from_ts: datetime,
    to_ts: datetime,
    *,
    client: httpx.Client | None = None,
) -> list[dict]:
    """Return blocked-domain events for [from_ts, to_ts). Empty if unset or API fails."""
    creds = _credentials()
    if creds is None:
        return []
    api_key, profile_id = creds
    owns_client = client is None
    http = client or httpx.Client(base_url=API_BASE, timeout=_TIMEOUT_SEC)
    events: list[dict] = []
    try:
        params: dict[str, Any] = {
            "from": _iso(from_ts),
            "to": _iso(to_ts),
            "status": "blocked",
            "limit": _PAGE_LIMIT,
            "sort": "asc",
        }
        cursor: str | None = None
        for _ in range(_MAX_PAGES):
            query = dict(params)
            if cursor:
                query["cursor"] = cursor
            try:
                response = http.get(
                    f"/profiles/{profile_id}/logs",
                    headers=_headers(api_key),
                    params=query,
                )
            except httpx.HTTPError as exc:
                logger.warning("NextDNS logs request failed: %s", exc)
                return events
            if response.status_code >= 400:
                logger.warning(
                    "NextDNS logs GET failed: %s %s",
                    response.status_code,
                    (response.text or "")[:200],
                )
                return events
            try:
                payload = response.json()
            except ValueError:
                logger.warning("NextDNS logs response was not JSON")
                return events
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                rows = []
            for item in rows:
                if isinstance(item, dict):
                    mapped = _map_log_entry(item)
                    if mapped is not None:
                        events.append(mapped)
            meta = payload.get("meta") if isinstance(payload, dict) else None
            pagination = (meta or {}).get("pagination") if isinstance(meta, dict) else None
            next_cursor = None
            if isinstance(pagination, dict):
                raw_cursor = pagination.get("cursor")
                if isinstance(raw_cursor, str) and raw_cursor:
                    next_cursor = raw_cursor
            if not next_cursor:
                break
            cursor = next_cursor
        return events
    except Exception:
        logger.exception("NextDNS logs pull failed")
        return events
    finally:
        if owns_client:
            http.close()


def fetch_dns_log_events(
    from_ts: datetime,
    to_ts: datetime,
    *,
    status: str = "blocked",
    limit: int = 200,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, str]], str | None]:
    """Admin DNS log viewer: return (events, next_cursor).

    Events are ``{at, domain, status}``. Raises ValueError if credentials unset
    (caller maps to 503). On HTTP failure returns whatever was collected (often []).
    """
    creds = _credentials()
    if creds is None:
        raise ValueError("nextdns_unset")
    api_key, profile_id = creds
    status_filter = (status or "blocked").strip().lower() or "blocked"
    page_limit = max(1, min(int(limit), _PAGE_LIMIT))
    owns_client = client is None
    http = client or httpx.Client(base_url=API_BASE, timeout=_TIMEOUT_SEC)
    events: list[dict[str, str]] = []
    next_cursor: str | None = None
    try:
        params: dict[str, Any] = {
            "from": _iso(from_ts),
            "to": _iso(to_ts),
            "limit": page_limit,
            "sort": "desc",
        }
        if status_filter not in ("", "all", "*"):
            params["status"] = status_filter
        cursor: str | None = None
        for _ in range(_MAX_PAGES):
            if len(events) >= page_limit:
                break
            query = dict(params)
            if cursor:
                query["cursor"] = cursor
            try:
                response = http.get(
                    f"/profiles/{profile_id}/logs",
                    headers=_headers(api_key),
                    params=query,
                )
            except httpx.HTTPError as exc:
                logger.warning("NextDNS admin logs request failed: %s", exc)
                break
            if response.status_code >= 400:
                logger.warning(
                    "NextDNS admin logs GET failed: %s %s",
                    response.status_code,
                    (response.text or "")[:200],
                )
                break
            try:
                payload = response.json()
            except ValueError:
                logger.warning("NextDNS admin logs response was not JSON")
                break
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                rows = []
            for item in rows:
                if not isinstance(item, dict):
                    continue
                domain = str(item.get("domain") or "").strip()
                if not domain:
                    continue
                st = str(item.get("status") or "").strip().lower() or "unknown"
                if status_filter not in ("", "all", "*") and st != status_filter:
                    continue
                at = str(item.get("timestamp") or item.get("at") or "")
                events.append({"at": at, "domain": domain, "status": st})
                if len(events) >= page_limit:
                    break
            meta = payload.get("meta") if isinstance(payload, dict) else None
            pagination = (meta or {}).get("pagination") if isinstance(meta, dict) else None
            next_cursor = None
            if isinstance(pagination, dict):
                raw_cursor = pagination.get("cursor")
                if isinstance(raw_cursor, str) and raw_cursor:
                    next_cursor = raw_cursor
            if not next_cursor or len(events) >= page_limit:
                break
            cursor = next_cursor
        return events[:page_limit], next_cursor
    except Exception:
        logger.exception("NextDNS admin logs pull failed")
        return events[:page_limit], next_cursor
    finally:
        if owns_client:
            http.close()


def enrich_incident_dns(payload: dict) -> dict:
    """Fill payload.dns from NextDNS when available is false/empty and env is set.

    Mutates a shallow copy. On missing env or pull failure, leaves available false.
    """
    out = dict(payload or {})
    dns = dict(out.get("dns") or {}) if isinstance(out.get("dns"), dict) else {}
    existing_events = list(dns.get("events") or []) if isinstance(dns.get("events"), list) else []
    if dns.get("available") and existing_events:
        out["dns"] = dns
        return out

    if _credentials() is None:
        if "dns" not in out:
            out["dns"] = {"available": False, "events": existing_events}
        return out

    bounds = _window_bounds(out)
    if bounds is None:
        return out

    from_ts, to_ts = bounds
    pulled = fetch_blocked_domains(from_ts, to_ts)
    if not pulled:
        return out

    merged = _merge_dns_events(existing_events, pulled)
    updated = dict(dns)
    updated["available"] = True
    updated["events"] = merged
    if "unavailableReason" in updated:
        updated["unavailableReason"] = None
    out["dns"] = updated
    return out
