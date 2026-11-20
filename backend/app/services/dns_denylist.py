"""Build DNS policy from CountryRestriction rows (applyTo dns|internet).

NextDNS fact (api.nextdns.io): country ccTLDs map to security.tlds (e.g. cn, ru);
curated hosts map to denylist entries. Wildcard strings like "*.cn" are not used.
Phase 2C: merge threat hosts; `*.example` never pushed to NextDNS.
"""

from __future__ import annotations

from typing import Any, Iterable

from app.data.dns_country_domains import COUNTRY_CCTLD, COUNTRY_DOMAIN_SEEDS
from app.data.threat_hosts import THREAT_HOSTS_BUILTIN, is_example_tld_host, threat_hosts


def _apply_to_list(row: Any) -> list[str]:
    if isinstance(row, dict):
        raw = row.get("apply_to") or row.get("applyTo") or []
    else:
        raw = getattr(row, "apply_to", None) or []
    return [str(a).lower() for a in raw]


def _countries(row: Any) -> list[str]:
    if isinstance(row, dict):
        raw = row.get("countries") or []
    else:
        raw = getattr(row, "countries", None) or []
    return [str(c).upper() for c in raw]


def _enabled(row: Any) -> bool:
    if isinstance(row, dict):
        return bool(row.get("enabled", True))
    return bool(getattr(row, "enabled", True))


def managed_seed_domains() -> set[str]:
    """Hosts ElderShield owns on NextDNS denylist (safe to delete on sync)."""
    out: set[str] = set()
    for hosts in COUNTRY_DOMAIN_SEEDS.values():
        out.update(h.lower() for h in hosts)
    # Include builtin examples so a prior mistaken push can be removed.
    out.update(h.lower() for h in THREAT_HOSTS_BUILTIN)
    out.update(h.lower() for h in threat_hosts(for_nextdns=False))
    return out


def build_dns_denylist(rows: Iterable[Any]) -> dict[str, Any]:
    """Return countries, NextDNS security.tlds ids, and denylist hostnames."""
    countries: set[str] = set()
    tlds: set[str] = set()
    domains: set[str] = set()

    for row in rows:
        if not _enabled(row):
            continue
        apply = _apply_to_list(row)
        if not any(a in ("dns", "internet") for a in apply):
            continue
        for iso in _countries(row):
            countries.add(iso)
            cctld = COUNTRY_CCTLD.get(iso)
            if cctld:
                tlds.add(cctld.lower())
            for host in COUNTRY_DOMAIN_SEEDS.get(iso, []):
                domains.add(host.lower())

    threat_all = threat_hosts(for_nextdns=False)
    threat_push = threat_hosts(for_nextdns=True)
    domains.update(threat_push)

    return {
        "source": "country_restrictions+threat_hosts",
        "countries": sorted(countries),
        "tlds": sorted(tlds),
        "domains": sorted(domains),
        "threatHosts": sorted(threat_push),
        "threatHostsLab": sorted(h for h in threat_all if is_example_tld_host(h)),
        "count": len(domains) + len(tlds),
    }
