from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from app.models.incident import Incident

FORBIDDEN_CALL_PHONE_KEYS = frozenset({"phoneNumber", "number", "raw", "msisdn"})
_FORBIDDEN_LOWER = frozenset(k.lower() for k in FORBIDDEN_CALL_PHONE_KEYS)


class IncidentSanitizeError(ValueError):
    pass


def should_merge(existing_triggered_at: datetime, new_triggered_at: datetime, window_seconds: int = 3600) -> bool:
    return abs((new_triggered_at - existing_triggered_at).total_seconds()) <= window_seconds


def merge_payloads(base: dict, incoming: dict) -> dict:
    out = dict(base)
    out["triggers"] = sorted(set(base.get("triggers", [])) | set(incoming.get("triggers", [])))
    calls = list(base.get("calls") or [])
    seen = {(c.get("phoneHash"), c.get("at")) for c in calls}
    for c in incoming.get("calls") or []:
        key = (c.get("phoneHash"), c.get("at"))
        if key not in seen:
            calls.append(c)
            seen.add(key)
    out["calls"] = calls
    apps = list(base.get("apps") or [])
    apk = {a.get("packageName") for a in apps}
    for a in incoming.get("apps") or []:
        if a.get("packageName") not in apk:
            apps.append(a)
            apk.add(a.get("packageName"))
    out["apps"] = apps
    b_dns, i_dns = base.get("dns") or {}, incoming.get("dns") or {}
    if i_dns.get("available"):
        out["dns"] = i_dns
    else:
        out["dns"] = b_dns if b_dns else i_dns
    for k in ("countryHints", "protectionSnapshot", "window"):
        if incoming.get(k):
            out[k] = incoming[k]
    return out


def strip_raw_phone_keys(obj: Any) -> Any:
    """Drop raw-phone keys anywhere in a JSON-like structure. Never persist those fields."""
    if isinstance(obj, dict):
        return {
            k: strip_raw_phone_keys(v)
            for k, v in obj.items()
            if str(k).lower() not in _FORBIDDEN_LOWER
        }
    if isinstance(obj, list):
        return [strip_raw_phone_keys(v) for v in obj]
    return obj


def sanitize_calls(calls: list[Any] | None) -> list[dict]:
    """Reject call entries that include raw phone fields; return copies without those keys.

    422 if a call has phoneNumber/number/raw/msisdn, or has any of those phone-like
    fields without phoneHash. Callers must not persist the original dicts.
    """
    cleaned: list[dict] = []
    for raw in calls or []:
        if not isinstance(raw, dict):
            raise IncidentSanitizeError("invalid_call_entry")
        if any(str(key).lower() in _FORBIDDEN_LOWER for key in raw):
            raise IncidentSanitizeError("raw_phone_forbidden")
        cleaned.append(dict(raw))
    return cleaned


def purge_old_incidents(session: Session, days: int = 90) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = list(session.exec(select(Incident).where(Incident.created_at < cutoff)).all())
    for row in rows:
        session.delete(row)
    return len(rows)
