"""DNS/internet policy derived from CountryRestriction applyTo dns|internet."""

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
    assert out["source"] == "country_restrictions"


def test_call_only_restriction_does_not_contribute_domains():
    rows = [
        {
            "countries": ["CN"],
            "apply_to": ["call"],
            "enabled": True,
        }
    ]
    out = build_dns_denylist(rows)
    assert out["domains"] == []
    assert out["tlds"] == []
    assert out["countries"] == []


def test_disabled_or_internet_apply_to():
    rows = [
        {"countries": ["RU"], "apply_to": ["internet"], "enabled": True},
        {"countries": ["CN"], "apply_to": ["dns"], "enabled": False},
    ]
    out = build_dns_denylist(rows)
    assert "RU" in out["countries"]
    assert "ru" in out["tlds"]
    assert "CN" not in out["countries"]
