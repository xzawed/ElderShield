# ElderShield (실버실드)

부모님 Android 기기용 방어적 Guard 시스템. 위험 국가 전화·인터넷 차단 + 사기앱 탐지.  
관리자만 웹 대시보드로 제어. 부모님은 설치·권한 후 조작 없음.

**설계 SSOT**: `docs/specs/2026-11-18-eldershield-system-design.md` (루트 `ElderShield_Design_v1.0.md`는 스텁)  
**문서 인덱스**: `docs/README.md` — `specs/`(결정), `plans/`(구현 서사), `00`/`01`/`06`(요약)  
**스프린트**: `docs/plans/2026-11-19-sprint-board.md` (Hybrid C · TDD · 교차 실측). 문서 비대화 금지(보드는 Status만 갱신)

## 역할 분담 (이 세션)

- **Grok**: 주 실행 — 보일러플레이트, CRUD/API, 테스트 백필, 기계적 리팩터, 모듈 구현
- **오케스트레이터(Composer/Claude)**: 아키텍처·보안·API 형태 결정, Grok diff 리뷰, 커밋 여부 판단
- **자동 커밋 금지**. 리뷰 후 사용자가 커밋 요청할 때만 커밋

## 하드 제약 (위반 금지)

- 부모님 불편 제로: 알림/팝업 최소화, 무인지 규칙·앱 업데이트
- 은행 앱 호환: **VpnService 기본 비활성**. Overlay / Accessibility / Device Admin **사용 금지**
- 합법적 방어만 (역공격·강제 삭제 없음)
- Bitdefender 병행 (SSOT §1.2.1): CallScreening 역할 강탈·BD 비활성 지시 금지. 미보유 시 전화 경로만 Off + 관리자 보고
- 배터리·WorkManager 제약 준수
- 제한 국가는 **다중 선택 유지** (`countries`는 항상 배열)

## 스택·구현 순서

1. **Backend 먼저**: FastAPI + SQLAlchemy/SQLModel + Alembic
2. 데이터 모델·관리자 API + 간단 웹 UI (HTMX 또는 Vue)
3. **Android** (`com.eldershield`): Room 캐시, CallScreeningService, WorkManager, AppScanner
4. TDD: 국가코드 매칭·화이트리스트부터 Red-Green-Refactor
5. 인터넷 차단: Private DNS (NextDNS/AdGuard) 중심. VpnService는 Phase 후반 옵션

## 아키텍처 요약

```
관리자 웹 ──HTTPS+API Key──▶ Backend ──주기 Pull(WorkManager)──▶ Android App
```

핵심 Android: CallScreeningService, RuleSyncWorker, AppScanner, DnsMonitor, Room

## 인증

- `X-API-Key` — **기기용 / 관리자용 키 분리** (`change-me-*` 기동 거부)
- HTTPS 필수. 전화번호 원문 등 민감 정보 최소화

## 핵심 모델

- `CountryRestriction`: `countries[]` (ISO alpha-2), `applyTo` (`call`|`dns`|`internet`), `version`(행)
- `CallRule`, `AppRiskRule`, `Device`, `RuleBundle` (**`version` = 단조 generation**)

기기 API: `GET /rules/latest`, `POST /devices/heartbeat`, `POST /devices/apps/scan-result`  
관리자 API: country-restrictions CRUD, call-rules, countries, devices, rules rollback  
Base: `/api/v1`

## Android 패키지

```
com.eldershield/{data,domain,service,scanner,ui}
```

minSdk 29. 대상: Note 10+ / Tab 계열. 테스트: S22 Ultra.

## 작업 규칙

- 설계 문서 스펙을 임의로 바꾸지 말 것. 필요 시 문서 먼저 제안·갱신
- Backend → Android 순. 규칙 모델·API를 먼저 고정
- 매칭/차단 로직은 단위 테스트 필수
- 부모님 UI에 상태/알림을 노출하지 말 것 (관리자 보고만)
- **구현 전 검증 룰**: 서술·가정은 공식 문서/실측으로 사실 확인 → 대안 대비 **최적·권장안**인지 판정 → 그다음에만 코드. 추측으로 API/제품 경로를 고정하지 말 것
