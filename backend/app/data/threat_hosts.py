"""Curated scam-ad / phishing host seeds for DNS denylist merge (Phase 2C P3).

OSS tree keeps synthetic `*.example` hosts for unit tests and shape checks.
Production operators add real FQDNs via gitignored `threat_hosts.local.json`
(see `threat_hosts.local.example.json`). Hosts under the reserved `example`
TLD are never pushed to NextDNS.
"""

from __future__ import annotations

import json
from pathlib import Path

# Lowercase FQDNs only (no wildcards). Used when no local overlay exists.
THREAT_HOSTS_BUILTIN: frozenset[str] = frozenset(
    {
        "scam-ad-landing.example",
        "fake-prize-popup.example",
        "crypto-airdrop-claim.example",
        "support-refund-verify.example",
        "bank-secure-login.example",
        "delivery-fee-pay.example",
        "account-locked-reset.example",
        "tax-refund-urgent.example",
        "parcel-customs-pay.example",
        "wallet-connect-phish.example",
        "free-giftcard-claim.example",
        "norton-renewal-fake.example",
        "microsoft-alert-verify.example",
        "kakao-secure-check.example",
        "toss-verify-login.example",
        "ad-click-jack.example",
        "overlay-offer-wall.example",
        "install-helper-apk.example",
        "remote-assist-scam.example",
        "gov-subsidy-form.example",
    }
)

_LOCAL_PATH = Path(__file__).resolve().parent / "threat_hosts.local.json"


def _load_local_hosts() -> frozenset[str] | None:
    if not _LOCAL_PATH.is_file():
        return None
    raw = json.loads(_LOCAL_PATH.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        hosts = raw.get("hosts") or raw.get("domains") or []
    elif isinstance(raw, list):
        hosts = raw
    else:
        raise ValueError("threat_hosts.local.json must be a list or {hosts:[...]}")
    cleaned = {str(h).strip().lower() for h in hosts if str(h).strip()}
    return frozenset(cleaned)


def is_example_tld_host(host: str) -> bool:
    h = host.strip().lower().rstrip(".")
    return h == "example" or h.endswith(".example")


def threat_hosts(*, for_nextdns: bool = False) -> frozenset[str]:
    """Return effective threat hosts. Drop `*.example` when preparing NextDNS push."""
    local = _load_local_hosts()
    base = local if local is not None else THREAT_HOSTS_BUILTIN
    if for_nextdns:
        return frozenset(h for h in base if not is_example_tld_host(h))
    return frozenset(base)


# Back-compat for imports / tests that expect THREAT_HOSTS
THREAT_HOSTS: frozenset[str] = threat_hosts(for_nextdns=False)
