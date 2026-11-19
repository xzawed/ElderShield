# 01. 아키텍처

**SSOT**: [`specs/2026-11-18-eldershield-system-design.md`](specs/2026-11-18-eldershield-system-design.md) §2–§5

## 구성

```
[ElderShield Admin UI — Jinja + HTMX + Tailwind CDN]
        │ HTTPS + API Key / HMAC session
        ▼
[ElderShield Backend (FastAPI)]
  - 규칙 저장 (버전 관리) · /admin/ui/* 콘솔
  - 기기 등록/상태 · 스캔 결과
        │ 주기적 Pull (WorkManager)
        ▼
[ElderShield Android App]
  - CallScreeningService · RuleSyncWorker
  - AppScanner · DnsMonitor · Room
```

**인터넷 차단**: Private DNS (NextDNS/AdGuard) 중심.  
로컬 VpnService는 Phase 후반 옵션 (은행 앱 테스트 후).

## 핵심 모델

- `CountryRestriction` — `countries[]`, `applyTo`, `version`(행)
- `CallRule`, `AppRiskRule`, `Device`
- `RuleBundle` — 앱 동기화 단위. **`version` = 단조 generation** (행 max 아님)

상세 JSON 스키마는 설계 §3.

## API

- Base: `/api/v1`, 헤더 `X-API-Key` (device / admin 분리)
- 기기: `GET /rules/latest`, `POST /devices/heartbeat`, `POST /devices/apps/scan-result`
- 관리자: country-restrictions CRUD, call-rules, countries, devices, rules rollback

상세는 설계 §4.

## Android 패키지

```
com.eldershield/{data,domain,service,scanner,ui}
```

인터페이스·CallScreening·Worker 동작은 설계 §5.

## Admin UI

- **CSS:** Tailwind via CDN (Phase 1). Tokens: teal `brand`, ink sidebar.  
- **검증:** 브라우저 / Playwright MCP로 `/admin/ui/login` → restrictions → devices.  
- **런북:** [`runbooks/admin-ui.md`](runbooks/admin-ui.md)

## 구현 순서

1. Backend (모델·API 계약 고정)
2. Admin UI
3. Android (Room → Sync → Call screening → Scanner)
4. TDD로 매칭 로직부터
