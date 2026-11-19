"""Starter denylist seeds per ISO country for Private DNS (NextDNS/AdGuard).

Not exhaustive — curated high-signal hosts + ccTLD. Expand over time.
"""

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

COUNTRY_CCTLD: dict[str, str] = {
    "CN": "cn",
    "RU": "ru",
    "KP": "kp",
    "IR": "ir",
    "KR": "kr",
}
