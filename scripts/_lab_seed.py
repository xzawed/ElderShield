"""Seed KR-lab rules + probe denylist / NextDNS sync. Invoked by lab-batch-verify.ps1."""
from __future__ import annotations

import json
import os
import sys

import httpx

base = os.environ.get("ELDERSHIELD_LAB_URL", "http://127.0.0.1:8765").rstrip("/")
ah = {"X-API-Key": os.environ.get("ADMIN_API_KEY", "test-admin-key")}
dh = {"X-API-Key": os.environ.get("DEVICE_API_KEY", "test-device-key")}

rows = httpx.get(f"{base}/api/v1/admin/country-restrictions", headers=ah, timeout=20).json()
cn = next((r for r in rows if r.get("countries") == ["CN"]), None)
kr = next((r for r in rows if r.get("countries") == ["KR"]), None)
payload_cn = {
    "name": "Lab CN call+dns",
    "countries": ["CN"],
    "applyTo": ["call", "dns"],
    "enabled": True,
    "description": "KR-lab batch",
}
payload_kr = {
    "name": "Lab KR call",
    "countries": ["KR"],
    "applyTo": ["call"],
    "enabled": True,
    "description": "010 national normalize",
}
if cn:
    httpx.put(
        f"{base}/api/v1/admin/country-restrictions/{cn['id']}",
        headers=ah,
        json=payload_cn,
        timeout=20,
    ).raise_for_status()
else:
    httpx.post(
        f"{base}/api/v1/admin/country-restrictions",
        headers=ah,
        json=payload_cn,
        timeout=20,
    ).raise_for_status()
if kr:
    httpx.put(
        f"{base}/api/v1/admin/country-restrictions/{kr['id']}",
        headers=ah,
        json=payload_kr,
        timeout=20,
    ).raise_for_status()
else:
    httpx.post(
        f"{base}/api/v1/admin/country-restrictions",
        headers=ah,
        json=payload_kr,
        timeout=20,
    ).raise_for_status()

# Whitelist via recreate: API has POST list; keep existing if present
rules = httpx.get(f"{base}/api/v1/admin/call-rules", headers=ah, timeout=20)
if rules.status_code == 200 and not rules.json():
    httpx.post(
        f"{base}/api/v1/admin/call-rules",
        headers=ah,
        json={
            "countryCodes": [],
            "whitelist": ["+8613812345678", "+821011112222"],
            "enabled": True,
        },
        timeout=20,
    ).raise_for_status()

den = httpx.get(f"{base}/api/v1/admin/dns-denylist", headers=ah, timeout=20)
print("DEN", den.status_code, json.dumps(den.json() if den.status_code == 200 else den.text)[:500])
latest = httpx.get(f"{base}/api/v1/rules/latest", headers=dh, timeout=20).json()
print(
    "BUNDLE",
    latest.get("version"),
    [(r["countries"], r["applyTo"]) for r in latest.get("countryRestrictions") or []],
)
sync = httpx.post(f"{base}/api/v1/admin/dns-denylist/sync-nextdns", headers=ah, timeout=30)
print("SYNC", sync.status_code, sync.text[:300])
sys.exit(0 if den.status_code == 200 else 1)
