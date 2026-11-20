"""Regenerate backend/app/data/country_master.json + country_cctld.json.

Requires (dev only): pip install pycountry babel phonenumbers
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_MASTER = ROOT / "backend" / "app" / "data" / "country_master.json"
OUT_CCTLD = ROOT / "backend" / "app" / "data" / "country_cctld.json"


def main() -> int:
    try:
        import pycountry
        from babel import Locale
        from phonenumbers.data import _COUNTRY_CODE_TO_REGION_CODE as ccmap
    except ImportError:
        print("Install pycountry babel phonenumbers in the venv first.", file=sys.stderr)
        return 1

    ko = Locale.parse("ko")
    en = Locale.parse("en")
    region_to_cc: dict[str, int] = {}
    for code, regions in ccmap.items():
        for r in regions:
            if r == "001":
                continue
            region_to_cc.setdefault(r, code)

    rows = []
    for c in pycountry.countries:
        code = c.alpha_2
        name_en = en.territories.get(code) or getattr(c, "name", code)
        name_ko = ko.territories.get(code) or name_en
        calling = region_to_cc.get(code)
        calling_code = f"+{calling}" if calling else ""
        rows.append(
            {
                "code": code,
                "name_en": name_en,
                "name_ko": name_ko,
                "calling_code": calling_code,
            }
        )
    rows.sort(key=lambda r: r["code"])
    OUT_MASTER.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cctld = {r["code"]: ("uk" if r["code"] == "GB" else r["code"].lower()) for r in rows}
    OUT_CCTLD.write_text(
        json.dumps(cctld, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} countries → {OUT_MASTER}")
    print(f"wrote {len(cctld)} cctlds → {OUT_CCTLD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
