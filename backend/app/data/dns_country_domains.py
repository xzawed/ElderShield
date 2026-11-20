"""Starter denylist seeds per ISO country for Private DNS (NextDNS/AdGuard).

Not exhaustive — curated high-signal hosts + ccTLD. Expand over time.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

# Domains without leading "*." ; ccTLD entries use "*.xx" form in builder.
COUNTRY_DOMAIN_SEEDS: dict[str, list[str]] = {
    "CN": [
        "baidu.com",
        "qq.com",
        "weixin.qq.com",
        "wechat.com",
        "taobao.com",
        "tmall.com",
        "alipay.com",
        "jd.com",
        "bilibili.com",
        "douyin.com",
        "tiktok.com",
        "zhihu.com",
        "163.com",
        "sina.com.cn",
        "sohu.com",
    ],
    "RU": [
        "yandex.ru",
        "vk.com",
        "mail.ru",
        "ok.ru",
        "rutube.ru",
    ],
    "KP": [],
    "IR": [
        "aparat.com",
        "digikala.com",
    ],
    "KR": [],  # never seed KR by default for parents' daily use
}


@lru_cache(maxsize=1)
def _load_cctld() -> dict[str, str]:
    path = Path(__file__).with_name("country_cctld.json")
    return dict(json.loads(path.read_text(encoding="utf-8")))


# Full ISO set (known ccTLD mapping); seeds above remain curated.
COUNTRY_CCTLD: dict[str, str] = _load_cctld()
