"""Sync ElderShield DNS policy to a dedicated NextDNS profile.

Verified against https://nextdns.github.io/api/ (beta):
- PATCH /profiles/:id/security  with tlds: [{id: \"cn\"}, ...]
- POST/DELETE /profiles/:id/denylist for curated host seeds
Uses a dedicated profile — denylist PUT replace is avoided to reduce collateral.
"""

from __future__ import annotations

from typing import Any, Callable

import httpx

from app.data.dns_country_domains import COUNTRY_CCTLD
from app.services.dns_denylist import build_dns_denylist, managed_seed_domains

API_BASE = "https://api.nextdns.io"


class NextDnsNotConfigured(Exception):
    pass


class NextDnsSyncError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _headers(api_key: str) -> dict[str, str]:
    return {"X-Api-Key": api_key, "Accept": "application/json", "Content-Type": "application/json"}


def sync_policy_to_nextdns(
    rows: list[Any],
    *,
    api_key: str | None,
    profile_id: str | None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    if not api_key or not profile_id:
        raise NextDnsNotConfigured(
            "NEXTDNS_API_KEY and NEXTDNS_PROFILE_ID must be set for automatic sync"
        )

    plan = build_dns_denylist(rows)
    owns_client = client is None
    http = client or httpx.Client(base_url=API_BASE, timeout=30.0)
    try:
        tlds_result = _sync_tlds(http, api_key, profile_id, plan["tlds"])
        denylist_result = _sync_denylist(http, api_key, profile_id, plan["domains"])
        return {
            "ok": True,
            "profileId": profile_id,
            "plan": plan,
            "tlds": tlds_result,
            "denylist": denylist_result,
        }
    finally:
        if owns_client:
            http.close()


def _sync_tlds(
    http: httpx.Client,
    api_key: str,
    profile_id: str,
    desired_tlds: list[str],
) -> dict[str, Any]:
    r = http.get(f"/profiles/{profile_id}/security", headers=_headers(api_key))
    if r.status_code >= 400:
        raise NextDnsSyncError(f"GET security failed: {r.status_code} {r.text}", status_code=r.status_code)
    data = r.json().get("data") or r.json()
    current = {str(item.get("id", "")).lower() for item in (data.get("tlds") or []) if item.get("id")}
    managed = {v.lower() for v in COUNTRY_CCTLD.values()}
    keep = sorted((current - managed) | set(desired_tlds))
    body = {"tlds": [{"id": t} for t in keep]}
    p = http.patch(f"/profiles/{profile_id}/security", headers=_headers(api_key), json=body)
    if p.status_code >= 400:
        raise NextDnsSyncError(f"PATCH security failed: {p.status_code} {p.text}", status_code=p.status_code)
    return {"desired": desired_tlds, "applied": keep}


def _sync_denylist(
    http: httpx.Client,
    api_key: str,
    profile_id: str,
    desired_domains: list[str],
) -> dict[str, Any]:
    r = http.get(f"/profiles/{profile_id}/denylist", headers=_headers(api_key))
    if r.status_code >= 400:
        raise NextDnsSyncError(f"GET denylist failed: {r.status_code} {r.text}", status_code=r.status_code)
    payload = r.json()
    entries = payload.get("data") if isinstance(payload.get("data"), list) else payload
    if not isinstance(entries, list):
        entries = []
    current = {str(e.get("id", "")).lower() for e in entries if e.get("id")}
    managed = managed_seed_domains()
    desired = set(desired_domains)
    added: list[str] = []
    removed: list[str] = []
    for host in sorted(desired - current):
        pr = http.post(
            f"/profiles/{profile_id}/denylist",
            headers=_headers(api_key),
            json={"id": host},
        )
        # 204 success; 200 with errors possible per NextDNS docs
        if pr.status_code >= 400:
            raise NextDnsSyncError(
                f"POST denylist {host} failed: {pr.status_code} {pr.text}",
                status_code=pr.status_code,
            )
        added.append(host)
    for host in sorted((current & managed) - desired):
        dr = http.delete(f"/profiles/{profile_id}/denylist/{host}", headers=_headers(api_key))
        if dr.status_code >= 400:
            raise NextDnsSyncError(
                f"DELETE denylist {host} failed: {dr.status_code} {dr.text}",
                status_code=dr.status_code,
            )
        removed.append(host)
    return {"added": added, "removed": removed, "desiredCount": len(desired)}
