"""Admin UI Korean / English message catalogs."""

from __future__ import annotations

from typing import Callable

LANG_COOKIE = "es_admin_lang"
DEFAULT_LANG = "ko"
SUPPORTED = frozenset({"ko", "en"})

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "brand.sub": "Admin console",
        "nav.restrictions": "Country restrictions",
        "nav.call_rules": "Call rules",
        "nav.dns": "DNS denylist",
        "nav.devices": "Devices",
        "nav.allowlist": "App allowlist",
        "nav.audit": "Audit",
        "nav.logout": "Sign out",
        "nav.login": "Sign in",
        "lang.ko": "한국어",
        "lang.en": "English",
        "login.title": "Admin sign in",
        "login.sub": "Use the admin API key",
        "login.api_key": "Admin API key",
        "login.submit": "Sign in",
        "login.error_invalid": "Invalid API key",
        "login.error_rate": "Too many failed attempts. Try again later.",
        "restrictions.heading": "Country restrictions",
        "restrictions.sub": "Multi-select countries stay arrays for device matching",
        "restrictions.new": "New restriction",
        "restrictions.empty": "No restriction groups yet.",
        "restrictions.col_name": "Name",
        "restrictions.col_countries": "Countries",
        "restrictions.col_apply": "Apply to",
        "restrictions.col_enabled": "Enabled",
        "restrictions.edit": "Edit",
        "form.new_restriction": "New restriction",
        "form.edit_restriction": "Edit restriction",
        "form.sub_countries": "Countries stay multi-select arrays for device matching",
        "form.create_group": "Create group",
        "form.edit_group": "Edit group",
        "form.name": "Name",
        "form.countries": "Countries (multi-select)",
        "form.countries_hint": "Type to filter. Hold Ctrl/Cmd to select multiple.",
        "form.countries_filter": "Filter countries…",
        "form.apply_to": "Apply to",
        "form.apply_hint": "call → CallScreening. dns / internet → DNS denylist (NextDNS/AdGuard; not an on-device VPN).",
        "form.enabled": "Enabled",
        "form.description": "Description",
        "form.save": "Save",
        "form.cancel": "Cancel",
        "form.delete": "Delete group",
        "form.delete_confirm": "Delete this group?",
        "form.error_required": "Name, countries, and apply_to are required.",
        "call_rules.heading": "Call rules",
        "call_rules.sub": "Whitelist numbers for CallScreening (exact E.164 match)",
        "dns.heading": "DNS denylist",
        "dns.sub": "Built from country restrictions + threat hosts",
        "devices.heading": "Devices",
        "devices.sub": "Heartbeat and protection status",
        "allowlist.heading": "App allowlist",
        "allowlist.sub": "Packages excluded from scan reporting",
        "audit.heading": "Audit",
        "audit.sub": "Admin action history",
        "yes": "Yes",
        "no": "No",
    },
    "ko": {
        "brand.sub": "관리자 콘솔",
        "nav.restrictions": "국가 제한",
        "nav.call_rules": "통화 규칙",
        "nav.dns": "DNS 차단 목록",
        "nav.devices": "기기",
        "nav.allowlist": "앱 허용 목록",
        "nav.audit": "감사 로그",
        "nav.logout": "로그아웃",
        "nav.login": "로그인",
        "lang.ko": "한국어",
        "lang.en": "English",
        "login.title": "관리자 로그인",
        "login.sub": "관리자 API 키를 입력하세요",
        "login.api_key": "관리자 API 키",
        "login.submit": "로그인",
        "login.error_invalid": "API 키가 올바르지 않습니다",
        "login.error_rate": "실패 횟수가 너무 많습니다. 잠시 후 다시 시도하세요.",
        "restrictions.heading": "국가 제한",
        "restrictions.sub": "국가는 다중 선택 배열로 기기에 전달됩니다",
        "restrictions.new": "새 제한 그룹",
        "restrictions.empty": "제한 그룹이 없습니다.",
        "restrictions.col_name": "이름",
        "restrictions.col_countries": "국가",
        "restrictions.col_apply": "적용",
        "restrictions.col_enabled": "사용",
        "restrictions.edit": "편집",
        "form.new_restriction": "새 제한",
        "form.edit_restriction": "제한 편집",
        "form.sub_countries": "국가는 다중 선택 배열로 기기 매칭에 사용됩니다",
        "form.create_group": "그룹 만들기",
        "form.edit_group": "그룹 편집",
        "form.name": "이름",
        "form.countries": "국가 (다중 선택)",
        "form.countries_hint": "입력해 필터링하세요. Ctrl/Cmd로 여러 항목을 선택합니다.",
        "form.countries_filter": "국가 검색…",
        "form.apply_to": "적용 대상",
        "form.apply_hint": "call → 통화 스크리닝. dns / internet → DNS 차단 목록(NextDNS/AdGuard, 기기 VPN 아님).",
        "form.enabled": "사용",
        "form.description": "설명",
        "form.save": "저장",
        "form.cancel": "취소",
        "form.delete": "그룹 삭제",
        "form.delete_confirm": "이 그룹을 삭제할까요?",
        "form.error_required": "이름, 국가, 적용 대상은 필수입니다.",
        "call_rules.heading": "통화 규칙",
        "call_rules.sub": "통화 스크리닝 화이트리스트(정확한 E.164)",
        "dns.heading": "DNS 차단 목록",
        "dns.sub": "국가 제한 + 위협 호스트에서 생성",
        "devices.heading": "기기",
        "devices.sub": "하트비트 및 보호 상태",
        "allowlist.heading": "앱 허용 목록",
        "allowlist.sub": "스캔 보고에서 제외할 패키지",
        "audit.heading": "감사 로그",
        "audit.sub": "관리자 작업 기록",
        "yes": "예",
        "no": "아니오",
    },
}


def normalize_lang(value: str | None) -> str:
    if not value:
        return DEFAULT_LANG
    v = value.strip().lower()
    if v.startswith("ko"):
        return "ko"
    if v.startswith("en"):
        return "en"
    return DEFAULT_LANG if v not in SUPPORTED else v


def resolve_lang(request) -> str:
    raw = request.cookies.get(LANG_COOKIE)
    if raw in SUPPORTED:
        return raw
    accept = request.headers.get("accept-language", "")
    if accept.lower().startswith("en"):
        return "en"
    return DEFAULT_LANG


def make_translator(lang: str) -> Callable[[str], str]:
    catalog = MESSAGES.get(lang) or MESSAGES[DEFAULT_LANG]
    fallback = MESSAGES["en"]

    def t(key: str) -> str:
        return catalog.get(key) or fallback.get(key) or key

    return t
