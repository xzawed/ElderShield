# 01. 아키텍처

**SSOT**: [`specs/2026-11-18-eldershield-system-design.md`](specs/2026-11-18-eldershield-system-design.md) §2–§5  
**Phase 2 addendum**: [`specs/2026-11-20-phase2-ac-depth-quality-design.md`](specs/2026-11-20-phase2-ac-depth-quality-design.md)

## 구성

```
[ElderShield Admin UI — Jinja + HTMX + Tailwind CDN]
        │ HTTPS + API Key / HMAC session
        ▼
[ElderShield Backend (FastAPI)]
  - 규칙 저장 (버전 관리) · /admin/ui/* 콘솔
  - 기기 health · 스캔 · audit · allowlist · threat DNS
        │ 주기적 Pull (WorkManager)
        ▼
[ElderShield Android App]
  - CallScreeningService · RuleSyncWorker · DeviceReportWorker
  - AppScanner (overlay/a11y capability) · DnsMonitor · Room
```

**인터넷 차단**: Private DNS (NextDNS/AdGuard) + country denylist + Phase 2 threat-host merge.  
로컬 VpnService는 후순위 옵션 (은행 앱 회귀 후).

## 핵심 모델

- `CountryRestriction` — `countries[]`, `applyTo`, `version`(행)
- `CallRule`, `AppRiskRule`, `Device` (+ Phase 2 health 스냅샷 필드)
- `DeviceHealthEvent`, `AppAllowlist`, `AuditLog`
- `RuleBundle` — 앱 동기화 단위. **`version` = 단조 generation** (행 max 아님)

상세 JSON 스키마는 설계 §3 · Phase 2 §4.

## API

- Base: `/api/v1`, 헤더 `X-API-Key` (device / admin 분리)
- 기기: `GET /rules/latest`, `POST /devices/heartbeat` (health 확장), `POST /devices/health-events`, `POST /devices/apps/scan-result` (`reasons[]`)
- 관리자: country-restrictions CRUD, call-rules, countries, devices(+detail), dns-denylist/sync, app-allowlist, audit, rules rollback
- Liveness: `GET /health` → `status`, `devices`, `degradedDevices`, `bundleVersion`

상세는 설계 §4 · Phase 2 addendum.

## Android 패키지

```
com.eldershield/{data,domain,service,scanner,ui}
```

인터페이스·CallScreening·Worker 동작은 설계 §5.

## Admin UI

- **CSS:** Tailwind via CDN. Tokens: teal `brand`, ink sidebar.  
- **페이지:** restrictions · call-rules · dns-denylist · devices(+detail) · allowlist · audit  
- **검증:** `/admin/ui/login` → devices detail / allowlist / audit.  
- **런북:** [`runbooks/admin-ui.md`](runbooks/admin-ui.md)

## 구현 순서

1. Backend (모델·API 계약 고정)
2. Admin UI
3. Android (Room → Sync → Call screening → Scanner)
4. TDD로 매칭 로직부터
