from app.data.countries import COUNTRY_MASTER, country_label
from app.data.dns_country_domains import COUNTRY_CCTLD


def test_country_master_has_at_least_140_iso_entries() -> None:
    assert len(COUNTRY_MASTER) >= 140
    codes = {c["code"] for c in COUNTRY_MASTER}
    assert "KR" in codes and "CN" in codes and "US" in codes
    for row in COUNTRY_MASTER:
        assert row["code"]
        assert row.get("name_en")
        assert row.get("name_ko")


def test_country_label_switches_lang() -> None:
    kr = next(c for c in COUNTRY_MASTER if c["code"] == "KR")
    assert "한국" in country_label(kr, "ko") or country_label(kr, "ko") == "대한민국"
    assert "Korea" in country_label(kr, "en")


def test_cctld_covers_master_codes() -> None:
    assert len(COUNTRY_CCTLD) >= 140
    assert COUNTRY_CCTLD["CN"] == "cn"
    assert COUNTRY_CCTLD["GB"] == "uk"
