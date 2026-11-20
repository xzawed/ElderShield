# Phase 2 설계: 보호 깊이(C) → 운영 품질(A)

**Version**: 1.0  
**작성일**: 2026-11-20  
**지위**: Phase 1 SSOT ([`2026-11-18-eldershield-system-design.md`](2026-11-18-eldershield-system-design.md)) **addendum** — 하드 제약은 상속·강화  
**목표**: 가족 단위 ElderShield를 유지한 채 보호 표면·안정성을 깊게 하고, 이어서 운영 품질을 올린다.

---

## 1. 확정 결정

| 항목 | 선택 |
|------|------|
| 제품 축 | **A+C** (가족 제품). **B**(다조직·테넌트·RBAC)는 비범위 |
| 순서 | **C 먼저 → A** |
| C 범위 | 기기 건강 + 앱 위험(오버레이 가능 앱) + DNS/웹 위협 피드 + 전화 **경보만** |
| 광고·사기 팝업 | **P3**: 타 앱 오버레이/접근성 **능력** 탐지 + 사기 광고·피싱 호스트 DNS 차단 |
| 보류 | 스미싱 NotificationListener, VpnService, 발신 국가 차단, 강제 삭제, P4 화면 읽기 |

### 1.1 하드 제약 (Phase 1 동일)

- 부모님 불편 제로 · 무인지 규칙 반영
- Overlay / Accessibility / Device Admin **ElderShield가 사용 금지**
- VpnService 기본 비활성
- CallScreening 역할 강탈·Bitdefender 끄기 지시 금지 (§1.2.1)
- `countries`는 항상 배열
- 합법적 방어만 · 전화번호 원문 최소화

---

## 2. Phase 2C — 보호 깊이·안정성

### 2.1 C1 Device health

Heartbeat를 **스냅샷 + 구조화 신호**로 확장한다. 부모님 UI 없음.

| 필드 (camelCase API) | 의미 |
|---------------------|------|
| 기존 | `dnsConfigured`, `callScreeningEnabled`, peers, `lastRuleVersion` |
| `dnsHostClass` | 허용 리졸버 부류 문자열 (`nextdns` / `adguard` / `other` / `none`) — specifier 원문 저장 금지 |
| `lastSyncOk` | 마지막 Rule sync 성공 여부 |
| `lastSyncErrorCode` | 실패 시 짧은 코드 (`http_4xx`, `http_5xx`, `network`, `parse`, …) |
| `cachedBundleVersion` | Room 캐시 bundle generation |
| `protectionDegraded` | 서버/클라이언트가 계산 가능: DNS off ∨ role not held ∨ sync stale |

선택: `POST /api/v1/devices/health-events` 로 이벤트 append (`dns_drift`, `role_lost`, `sync_failed`) — heartbeat와 병행 가능.

Admin: 기기 상세에 last N events + “보호 저하” 배지.

### 2.2 C2 App risk + overlay scam capability (P3)

[`AppRiskScorer`](../../android/core/src/main/kotlin/com/eldershield/domain/scanner/AppRiskScorer.kt) 확장:

| 신호 | reason 코드 | 가중(권장) |
|------|-------------|-----------|
| `SYSTEM_ALERT_WINDOW` 선언 또는 `canDrawOverlays` | `overlay_permission` | +25 |
| AccessibilityService 선언(타 앱) | `accessibility_service_declared` | +25 (기존 bind와 합산 상한 유지) |

스캔 결과 API에 `reasons: string[]` 저장. Admin package allowlist(패키지+메모)로 오탐 억제.

**비범위**: 팝업 OCR, 실시간 오버레이 차단, 강제 삭제.

### 2.3 C3 DNS / web threat feed (P3)

- 버전된 **scam-ad / phishing host** 목록을 국가 denylist와 merge
- NextDNS sync 경로 재사용 (`security` denylist hosts)
- Android: Private DNS 이탈 → health `dns_drift`
- 한계(정직): IP 직결·앱 내장 DoH는 100% 불가

### 2.4 C4 Call — alerts only

- 발신 차단 없음 · 역할 강탈 없음
- `callScreeningEnabled` false 전환 + peers 존재 → admin 표면/이벤트 `role_lost`
- 알림 채널 실발송은 A2에서 연결 (C4는 저장·UI 배지)

### 2.5 C5 Stability

- Fail-open EmptyNoBlock 유지
- “degraded protection”은 관리자만 가시
- TDD: scorer / health schema / denylist merge 단위 테스트 필수

---

## 3. Phase 2A — 운영 품질 (C 이후)

| 순서 | 항목 | 요약 |
|------|------|------|
| A1 | Audit log | Admin 변경(restriction, call-rule, denylist sync, allowlist) append-only |
| A2 | Admin notify | Telegram 또는 webhook — high-risk scan, dns_drift, role_lost (`.env`) |
| A3 | Observability | `/health` 확장 + sync lag / last-seen 간단 메트릭 |
| A4 | Auth harden | Admin login rate-limit; 키 로테이션 런북 |
| A5 | Backup runbook | DB + NextDNS 프로필 |

다조직 RBAC는 **B** — 여기 없음.

---

## 4. API 계약 요약 (추가)

### 4.1 Heartbeat 확장 (`POST /devices/heartbeat`)

기존 필드 + optional:

```json
{
  "dnsHostClass": "nextdns",
  "lastSyncOk": true,
  "lastSyncErrorCode": null,
  "cachedBundleVersion": 5,
  "protectionDegraded": false
}
```

하위 호환: 새 필드 생략 시 서버 기본값.

### 4.2 Health events (`POST /devices/health-events`)

```json
{
  "deviceUuid": "...",
  "events": [
    { "type": "dns_drift", "at": "2026-11-20T00:00:00Z", "detail": "host_class=other" }
  ]
}
```

### 4.3 Scan-result 확장

`suspiciousApps[]` 항목에 `reasons: string[]` (optional, default `[]`).

### 4.4 Admin

- `GET /admin/devices/{deviceUuid}` — device + recent health + recent scans
- `POST/DELETE /admin/app-allowlist` — package allowlist
- `GET/PUT` threat-host list 또는 내장 데이터 파일 + sync
- `GET /admin/audit` (A1)
- Notify config via env only (A2)

---

## 5. 기술 조사 요약 (P3)

| 주제 | 결론 |
|------|------|
| 오버레이 “노출” 실시간 감지 | Accessibility/MediaProjection 필요 → **SSOT 위반** → 비채택 |
| 가능 앱 탐지 | `PackageManager` 권한·서비스 선언 + (가능 시) `Settings.canDrawOverlays`는 **자기 앱만** 정확; 타 앱은 권한 선언·AppOps 힌트 | 
| 사기 광고 경로 | DNS denylist에 랜딩/트래킹 호스트 추가가 은행앱·무조작과 가장 잘 맞음 |
| Admin 알림 | 기기 FCM이 아니라 **서버→Telegram/webhook** (부모님 무통지) |

---

## 6. 구현 순서

1. 본 스펙 + roadmap / sprint board  
2. C1 health  
3. C2 overlay scoring + schema  
4. C3 threat hosts + NextDNS  
5. C4 role_lost surface  
6. C 회귀  
7. A1→A5  

---

## 7. 비범위

- B 테넌트/다관리자  
- P4 화면 내용 탐지  
- ElderShield Overlay/Accessibility/Device Admin  
- SMS 리스너 (별도 게이트)  
- Public repo 전환 (운영 결정)
