# ElderShield 전체 일정 · WBS

**Version**: 1.0  
**작성일**: 2026-11-19  
**기준 문서**: [`../specs/2026-11-18-eldershield-system-design.md`](../specs/2026-11-18-eldershield-system-design.md)  
**가정**: 1인(또는 AI 에이전트 보조) 개발, 주 5일 · 일 4~6시간 유효 작업  
**총 기간(권장)**: **6주** (버퍼 포함 7주)

---

## 1. 목표 마일스톤

| ID | 마일스톤 | 완료 정의 (DoD) | 목표 주 |
|----|----------|-----------------|--------|
| M0 | 문서·규칙 고정 | AGENTS.md + 본 docs 세트 승인 | W0 |
| M1 | Backend API v1 | 규칙 CRUD·기기 API·버전 동기화·단위 테스트 통과 | W1–W2 |
| M2 | 관리자 최소 UI | 국가 다중 선택·기기 목록·스캔 결과 조회 | W2–W3 |
| M3 | Android 코어 | Room 캐시 + RuleSyncWorker + CallScreening 차단 | W3–W4 |
| M4 | 스캔·DNS 모니터 | AppScanner 보고 + Private DNS 상태 heartbeat | W4–W5 |
| M5 | 실기기 검증 | S22 Ultra 은행앱 호환 + Note 10+ 전화 차단 | W5–W6 |
| M6 | 내부 배포 준비 | Play 내부 테스트 트랙 + 롤백 절차 문서화 | W6 |

VpnService·NextDNS API 자동 연동은 **Phase 2** (본 일정 밖).

---

## 2. 주차별 일정

### W0 — 기획·테스트 기준 고정 (현재)
- 설계 문서 확정, AGENTS.md, 일정/기획검토/단위테스트 문서
- 저장소 구조 합의 (`backend/`, `android/`, `docs/`)
- 테스트 기기·은행 앱 목록 확정

### W1 — Backend 기반
- FastAPI 프로젝트, SQLModel, Alembic
- `CountryRestriction`, `CallRule`, `AppRiskRule`, `Device`, `RuleBundle` 스키마
- 관리자 API: country-restrictions CRUD, countries 마스터
- 단위 테스트: 모델·버전 증가·다중 `countries` 유지

### W2 — 기기 API + 관리자 UI 골격
- `GET /rules/latest`, heartbeat, scan-result
- API Key 분리 (device / admin)
- 관리자 UI: 국가 멀티셀렉트, 제한 그룹 CRUD
- 통합 스모크: 규칙 변경 → version++ → latest 반영

### W3 — Android 골격 + 동기화
- `com.eldershield` 앱, minSdk 29
- Room RuleBundle 캐시, RuleRepository
- RuleSyncWorker (PeriodicWork, 실패 시 무UI·캐시 유지)
- 단위 테스트: 버전 비교, 캐시 fallback

### W4 — 전화 차단 + 매칭 엔진
- `CountryRestrictionMatcher` (정규화·다중 국가·화이트리스트)
- CallScreeningService 연동 (알림 최소화)
- 단위 테스트: `+86` / `0086` / `86`, 화이트리스트 우선
- S22 Ultra 스모크: 정상 통화·차단 후보 번호

### W5 — AppScanner + DnsMonitor + 대시보드 연동
- installer ≠ Play Store / 위험 권한 점수
- 스캔 결과 서버 전송만 (로컬 알림 없음)
- Private DNS 설정 여부 heartbeat 필드
- 관리자: 기기 상태·의심 앱 목록

### W6 — 실기기·하드닝·배포
- Note 10+ 전화 차단, Tab 계열 설치 스모크
- 은행 앱(토스, 카카오뱅크 등) 회귀
- 롤백 API 검증, 감사 로그 최소 세트
- Play 내부 테스트 트랙 업로드

---

## 3. WBS (작업분해)

```
ElderShield
├── 0. 기획·문서
│   ├── 0.1 설계·AGENTS 고정
│   ├── 0.2 일정·검토·단위테스트 문서
│   └── 0.3 저장소/CI 골격
├── 1. Backend
│   ├── 1.1 프로젝트·DB·마이그레이션
│   ├── 1.2 도메인 모델·버전 로직
│   ├── 1.3 관리자 API
│   ├── 1.4 기기 API·인증
│   └── 1.5 롤백·감사 로그(최소)
├── 2. Admin Web
│   ├── 2.1 국가 멀티셀렉트 UI
│   ├── 2.2 제한 그룹 CRUD
│   └── 2.3 기기·스캔 결과 뷰
├── 3. Android
│   ├── 3.1 앱 골격·권한(Call Screening)
│   ├── 3.2 Room + Rule sync
│   ├── 3.3 Call screening matcher
│   ├── 3.4 AppScanner
│   └── 3.5 DnsMonitor(상태만)
├── 4. 품질
│   ├── 4.1 단위 테스트 (Backend + Android 순수 로직)
│   ├── 4.2 API 계약 테스트
│   └── 4.3 실기기 체크리스트
└── 5. 배포·운영
    ├── 5.1 환경변수·시크릿
    ├── 5.2 Play 내부 트랙
    └── 5.3 롤백 런북
```

---

## 4. 의존성 · 크리티컬 패스

```
문서 고정 → Backend 모델/API → Admin UI
                ↓
         Android Sync ←── RuleBundle 계약 고정
                ↓
         Call Screening (매칭 단위테스트 선행)
                ↓
         Scanner + DNS status → 실기기 → 내부 배포
```

**크리티컬 패스**: 규칙 모델·API 계약 고정 → Android 동기화 → 전화 매칭 → 실기기 전화 차단.

---

## 5. 리스크 · 버퍼

| 리스크 | 영향 | 완화 | 버퍼 |
|--------|------|------|------|
| 은행 앱과 권한/서비스 충돌 | M5 지연 | VpnService 기본 OFF, Overlay 등 금지 준수 | +3일 |
| Call Screening OEM 편차 | M4–M5 | S22 + Note 10+ 조기 스모크 | +2일 |
| Private DNS만으로 국가 차단 한계 | 기능 기대치 | Phase1은 상태 모니터+수동 NextDNS, Phase2 자동화 | 범위 고정 |
| API 계약 중도 변경 | Android 재작업 | M1에서 OpenAPI/스키마 동결 후 변경은 versioned | 검토 게이트 |

---

## 6. 역할 (실행)

| 역할 | 담당 |
|------|------|
| 구현·보일러플레이트·테스트 작성 | **Grok** (주 실행) |
| 아키텍처·보안·계약 변경·최종 리뷰 | 오케스트레이터 |
| 실기기 조작·Play 콘솔 | 사용자 |
| 커밋 | 사용자 요청 시에만 |

---

## 7. 주간 검토 리듬

- **일일**: Grok 산출 diff 리뷰 (보안·하드 제약·계약 위반 여부)
- **주 2회 (권장)**: 마일스톤 DoD 체크 ([`2026-11-19-development-plan-and-review.md`](2026-11-19-development-plan-and-review.md) 게이트)
- **마일스톤 종료**: 검토 체크리스트 전원 Pass 또는 명시적 Waive
