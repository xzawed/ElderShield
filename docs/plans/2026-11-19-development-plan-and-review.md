# ElderShield 개발 기획 · 검토 문서

**Version**: 1.0  
**작성일**: 2026-11-19  
**기준 문서**: [`../specs/2026-11-18-eldershield-system-design.md`](../specs/2026-11-18-eldershield-system-design.md), [`2026-11-19-phase1-schedule-wbs.md`](2026-11-19-phase1-schedule-wbs.md)  
**목적**: 무엇을·어떤 순서로·어떤 품질 게이트로 만들지 고정한다.

---

## 1. 제품 범위 (Phase 1 In / Out)

### In Scope
- 위험 국가 **전화 차단** (CallScreeningService + 로컬 규칙 캐시)
- **다중 국가** 제한 그룹 CRUD (관리자 웹)
- 규칙 **버전 동기화** (WorkManager Pull)
- **사기/출처불명 앱 탐지** → 서버 보고만 (부모님 알림 없음)
- Private DNS **설정 상태 모니터** + heartbeat
- DNS denylist + **NextDNS sync API** (운영 `NEXTDNS_*` 게이트)
- 관리자 대시보드: 기기 상태, 스캔 결과, 규칙 롤백

### Out of Scope (Phase 2+)
- VpnService 기반 IP 국가 필터
- 고도화 위험 점수·통계 대시보드
- iOS, 부모님용 풍부한 UI

### 비목표 (절대 하지 않음)
- Overlay / Accessibility / Device Admin
- 역공격, 원격 강제 삭제, 불법 수집
- 부모님 화면 상시 알림·팝업으로 상태 노출

---

## 2. 성공 기준 (Acceptance)

| ID | 기준 | 검증 |
|----|------|------|
| A1 | 제한 국가 착신/발신 후보 번호가 차단되고, 화이트리스트는 통과 | 단위 + 실기기 |
| A2 | 규칙 변경 후 부모 조작 없이 다음 sync에 반영, UI 노출 없음 | 실기기 관찰 |
| A3 | 은행 앱(토스, 카카오뱅크 등) 정상 동작 | S22 Ultra 체크리스트 |
| A4 | `countries` 다중 선택·저장·재편집 유지 | Admin UI + API 테스트 |
| A5 | 의심 앱이 대시보드에만 표시, 기기 로컬 알림 없음 | 스캔 E2E |
| A6 | device/admin API Key 분리, HTTPS | 설정·코드 리뷰 |

---

## 3. 기술 기획

### 3.1 권장 저장소 레이아웃

```
ElderShield/
├── AGENTS.md
├── docs/                    # Grok Build 관례: specs/ · plans/ · releases/
├── backend/                 # FastAPI + SQLModel + Alembic
│   ├── app/
│   │   ├── api/             # admin/, devices/
│   │   ├── models/
│   │   ├── services/        # versioning, matching helpers(서버측)
│   │   └── main.py
│   └── tests/
└── android/                 # com.eldershield
    ├── app/src/main/java/com/eldershield/...
    └── app/src/test/        # JVM 단위 (매칭 등)
```

### 3.2 Backend
- FastAPI, SQLModel(또는 SQLAlchemy), Alembic, pytest
- 인증: `X-API-Key` 헤더, 역할별 키
- `CountryRestriction` 변경 시 `version` 자동 증가 → `RuleBundle.version` 재계산
- OpenAPI 스키마를 Android 계약의 SSOT로 취급 (M1 종료 시 동결 권장)

### 3.3 Admin Web
- HTMX(단순) 또는 Vue SPA — Phase 1은 **CRUD 완결**이 우선
- 국가 마스터 `GET /admin/countries` 기반 **멀티셀렉트** 필수
- 기기·스캔은 읽기 중심

### 3.4 Android
- Kotlin, minSdk 29, Room, WorkManager, CallScreeningService
- 패키지: `data` / `domain` / `service` / `scanner` / `ui`(테스트·설정 최소)
- 네트워크 실패 시 **캐시 유지·크래시 금지·UI 없음**
- VpnService 모듈은 넣지 않거나 feature flag 기본 OFF

### 3.5 데이터·동기화 계약
- 동기화 단위: `RuleBundle` (`version`, `countryRestrictions`, `callRules`, `appRiskRules`, `updatedAt`)
- 앱: `lastRuleVersion`을 heartbeat에 포함
- 롤백: admin `POST /admin/rules/rollback` → 새 version으로 발행(히스토리 보존)

---

## 4. 개발 순서 (실행 백로그)

우선순위는 일정 문서 크리티컬 패스와 동일하다. Grok 위임 단위 권장 크기: **1개 수직 슬라이스 ≤ 반나절**.

| 순번 | 백로그 항목 | 산출물 | 선행 |
|------|-------------|--------|------|
| P1 | Backend 스캐폴드 + DB | 실행 가능한 FastAPI, Alembic | M0 |
| P2 | 도메인 모델 + 버전 로직 | 모델·서비스 + 단위테스트 | P1 |
| P3 | Admin country-restrictions API | CRUD + countries | P2 |
| P4 | Device rules/heartbeat/scan API | 기기 계약 | P2 |
| P5 | Admin UI 멀티셀렉트 | 브라우저에서 다중 국가 유지 | P3 |
| P6 | Android 스캐폴드 + Room | 캐시 Entity/DAO | P4 계약 |
| P7 | RuleSyncWorker | Pull + 실패 내성 | P6 |
| P8 | Matcher + CallScreening | 차단 동작 | P7 |
| P9 | AppScanner + 보고 | 대시보드 표시 | P4, P5 |
| P10 | DnsMonitor + 실기기 패스 | A2–A5 | P8, P9 |

---

## 5. 검토 체계

### 5.1 검토 유형

| 게이트 | 시점 | 담당 | 초점 |
|--------|------|------|------|
| G-Design | 스펙/계약 변경 전 | 오케스트레이터 | 하드 제약·범위 |
| G-PR/Diff | Grok 산출마다 | 오케스트레이터 | 정확성·보안·범위 이탈 |
| G-Milestone | M1–M6 종료 | 오케스트레이터+사용자 | DoD·Acceptance |
| G-Device | M5 | 사용자 | 실기기 체크리스트 |
| G-Release | M6 | 사용자 | 내부 트랙·롤백 런북 |

### 5.2 Diff 리뷰 체크리스트 (매 Grok 산출)

- [ ] 하드 제약 위반 없음 (VpnService 기본 ON, Overlay, Accessibility, Device Admin 금지)
- [ ] 부모님 향 UI/알림 추가 없음
- [ ] `countries`가 단일 값이 아닌 **배열**로 유지
- [ ] API Key·시크릿 하드코딩 없음
- [ ] 설계 문서에 없는 엔드포인트/필드 무단 추가 없음 (필요 시 문서 선변경)
- [ ] 테스트 추가/갱신 여부 (해당 모듈)
- [ ] 배터리·WorkManager 제약 무시하는 루프/포그라운드 남용 없음

### 5.3 마일스톤 검토 체크리스트

**M1 Backend**
- [ ] `/api/v1` admin·device 라우트 동작
- [ ] 제한 생성/수정 시 version 증가
- [ ] pytest 단위·API 테스트  greenc
- [ ] OpenAPI와 설계 3·4장 정합

**M2 Admin UI**
- [ ] 다중 국가 선택·저장·재오픈 유지
- [ ] 기기 목록·스캔 결과 조회
- [ ] 롤백 트리거(또는 준비) 가능

**M3–M4 Android 코어**
- [ ] sync 실패 시 캐시 유지
- [ ] 매칭 단위테스트 전부 Pass ([`../specs/2026-11-19-unit-test-design.md`](../specs/2026-11-19-unit-test-design.md))
- [ ] CallScreening 권한 플로우 문서화

**M5 실기기**
- [ ] 설계 8장 실기기 항목 Pass
- [ ] 은행 앱 회귀 Pass
- [ ] 무인지 규칙 반영 확인

**M6 배포**
- [ ] 내부 테스트 트랙 빌드
- [ ] 롤백 절차 1페이지 런북
- [ ] 키·환경 분리 확인

### 5.4 결함 등급

| 등급 | 정의 | 조치 |
|------|------|------|
| Blocker | 하드 제약 위반, 은행앱 장애, 키 유출 | 즉시 중단·수정 |
| Major | 차단/동기화 오동작, 데이터 손실 | 마일스톤 통과 불가 |
| Minor | UI/카피/로그 이슈 | 백로그 수용 가능 |
| Waive | 범위상 의도적 미구현 | 문서에 사유·Phase 기록 |

---

## 6. 환경 · 보안 기획 (최소)

- Backend: `.env` (ADMIN_API_KEY, DEVICE_API_KEY, DATABASE_URL) — 커밋 금지
- Android: BuildConfig/로컬 properties로 base URL·device key (저장소 시크릿 스캔)
- 전송: HTTPS만
- 로그: 전화번호 원문 저장/로그 금지 (해시·국가코드 수준만)
- 감사: 규칙 변경 actor·timestamp·version 최소 기록

---

## 7. 산출물 목록

| 산출물 | 위치(예정) |
|--------|------------|
| 설계 (SSOT) | `docs/specs/2026-11-18-eldershield-system-design.md` |
| 에이전트 규칙 | `AGENTS.md` |
| 일정 | `docs/plans/2026-11-19-phase1-schedule-wbs.md` |
| 본 기획·검토 | `docs/plans/2026-11-19-development-plan-and-review.md` |
| 단위테스트 설계 | `docs/specs/2026-11-19-unit-test-design.md` |
| OpenAPI | `backend/openapi.json` (생성) |
| 실기기 체크리스트 | 설계 8장 + M5 게이트 |
| 롤백 런북 | `docs/runbooks/rollback.md` (M6) |

---

## 8. 변경 관리

1. 설계 문서 수정 PR/요청 → G-Design 승인  
2. AGENTS.md·본 docs 동시 갱신  
3. 이미 구현된 계약 변경 시 `RuleBundle.version` 정책과 Android 호환성 명시  
4. 구현은 승인 후에만 Grok 위임

---

## 9. 다음 액션

문서 승인 후:
1. Backend 스캐폴드부터 Grok 위임 (P1)
2. P2와 함께 `docs/specs/2026-11-19-unit-test-design.md`의 Backend 케이스부터 TDD
