"""DNS/internet policy derived from CountryRestriction applyTo dns|internet."""

from app.data.threat_hosts import THREAT_HOSTS_BUILTIN, is_example_tld_host
from app.services.dns_denylist import build_dns_denylist


def test_cn_dns_restriction_includes_tld_and_major_hosts():
    rows = [
        {
            "countries": ["CN"],
            "apply_to": ["dns"],
            "enabled": True,
        }
    ]
    out = build_dns_denylist(rows)
    assert "cn" in out["tlds"]
    assert "*.cn" not in out["domains"]
    assert "baidu.com" in out["domains"]
    assert "CN" in out["countries"]
    assert out["source"] == "country_restrictions+threat_hosts"
    # Lab `*.example` seeds never go to NextDNS domains / threatHosts
    assert "scam-ad-landing.example" not in out["domains"]
    assert "scam-ad-landing.example" not in out["threatHosts"]
    assert all(is_example_tld_host(h) for h in out["threatHostsLab"])
    # Without a local overlay, lab list equals builtin; with overlay, lab may be empty.
    assert set(out["threatHostsLab"]).issubset(set(THREAT_HOSTS_BUILTIN))
    assert all(not is_example_tld_host(h) for h in out["threatHosts"])


def test_call_only_restriction_does_not_contribute_country_policy():
    rows = [
        {
            "countries": ["CN"],
            "apply_to": ["call"],
            "enabled": True,
        }
    ]
    out = build_dns_denylist(rows)
    assert out["tlds"] == []
    assert out["countries"] == []
    assert "baidu.com" not in out["domains"]
    assert "scam-ad-landing.example" not in out["domains"]


def test_disabled_or_internet_apply_to():
    rows = [
        {"countries": ["RU"], "apply_to": ["internet"], "enabled": True},
        {"countries": ["CN"], "apply_to": ["dns"], "enabled": False},
    ]
    out = build_dns_denylist(rows)
    assert "RU" in out["countries"]
    assert "ru" in out["tlds"]
    assert "CN" not in out["countries"]
