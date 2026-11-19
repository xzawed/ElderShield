# ElderShield 단위 테스트 설계

> Grok Build `docs/specs/` — 테스트 전략·케이스 ID의 설계 기록.

**Version**: 1.0  
**작성일**: 2026-11-19  
**기준 문서**: [`2026-11-18-eldershield-system-design.md`](2026-11-18-eldershield-system-design.md) §5–§8  
**일정**: [`../plans/2026-11-19-phase1-schedule-wbs.md`](../plans/2026-11-19-phase1-schedule-wbs.md) (M5 실기기)  
**원칙**: TDD — 매칭·버전·다중 국가 로직은 **구현 전 Red**, 그다음 Green/Refactor  
**범위**: JVM/파이썬 **단위** 테스트. 실기기는 별도 체크리스트(설계 §8, 일정 M5).

---

## 1. 목표 · 범위

### 목표
- 전화 차단·규칙 동기화·앱 위험 판정의 **결정적 로직**을 자동화로 잠근다.
- 회귀 시 실기기 전에 CI에서 실패를 잡는다.

### In Scope (Unit)
- 국가코드 정규화·매칭·화이트리스트
- 다중 `countries` / 다중 `CountryRestriction` 그룹
- RuleBundle 버전 비교·캐시 선택
- AppScanner 위험 점수(순수 함수)
- Backend: 버전 증가, CRUD 불변조건, API 핸들러(DB 테스트 더블/SQLite)

### Out of Scope (Unit이 아님)
- CallScreeningService OEM 바인딩, WorkManager 스케줄러 실기기 동작
- Private DNS 시스템 설정 UI
- 은행 앱 호환성
- 실제 NextDNS 차단 효과

이들은 **실기기/수동** 또는 상위 통합 테스트로 둔다.

---

## 2. 도구 · 디렉터리

| 영역 | 도구 | 위치(권장) | 실행 |
|------|------|------------|------|
| Backend | pytest, httpx/AsyncClient, SQLite in-memory | `backend/tests/` | `pytest -q` |
| Android 순수 로직 | JUnit5 | `android/core/src/test/` (`:core` JVM) | `./gradlew :core:test` |
| CI (추후) | 위 두 명령 | PR 게이트 | M1부터 Backend, M3부터 Android |

**테스트 더블**: 네트워크·PackageManager·CallScreening은 인터페이스로 격리 후 fake.

---

## 3. 품질 게이트

| 게이트 | 조건 |
|--------|------|
| 모듈 머지 | 해당 패키지 단위테스트 100% Pass |
| M1 | Backend 표 §5 필수 케이스 Pass |
| M4 | Android 매칭·버전 표 §4 필수 케이스 Pass |
| 커버리지(권장) | `domain`/`services` 매칭·버전 로직 **라인 ≥ 80%** (UI·생성 코드 제외) |

실패 시: 구현 추가 금지, 테스트 먼저 수정(의도 변경이면 본 문서·설계 선수정).

---

## 4. Android — 도메인 단위 테스트

대상 인터페이스(설계 §5.2):

```kotlin
CountryRestrictionMatcher.shouldBlockCall(phoneNumber, rules): Boolean
CountryRestrictionMatcher.getRestrictedCountries(rules): Set<String>
RuleRepository / version 비교 유틸
AppScanner 위험 점수 순수 함수 (PackageManager는 fake)
```

### 4.1 국가코드 정규화 · 매칭 (필수)

| ID | 시나리오 | 입력 | 규칙 | 기대 |
|----|----------|------|------|------|
| UT-A-01 | E.164 | `+8613812345678` | CN in applyTo=call | block=true |
| UT-A-02 | 00 접두 | `008613812345678` | CN | block=true |
| UT-A-03 | 국가코드만 숫자 | `8613812345678` | CN | block=true |
| UT-A-04 | 한국 번호 | `+821012345678` | CN,RU만 | block=false |
| UT-A-05 | 러시아 | `+79161234567` | RU | block=true |
| UT-A-06 | 비활성 규칙 | `+86...` | CN, enabled=false | block=false |
| UT-A-07 | applyTo에 call 없음 | `+86...` | applyTo=[dns]만 | block=false |
| UT-A-08 | 빈 번호/널성 | `""` / 공백 | 임의 | block=false, 예외 없음 |
| UT-A-09 | 짧은 번호 | `1234` | 임의 | block=false |

### 4.2 다중 국가 · 다중 그룹 (필수)

| ID | 시나리오 | 기대 |
|----|----------|------|
| UT-A-10 | 한 그룹에 CN,RU,KP,IR | 각 코드 번호 모두 block |
| UT-A-11 | 그룹 A=CN, 그룹 B=RU (둘 다 enabled) | 양쪽 번호 block |
| UT-A-12 | 그룹 A disabled, B enabled | A 국가만 통과, B 차단 |
| UT-A-13 | `getRestrictedCountries` | enabled+call 그룹의 합집합 |

### 4.3 화이트리스트 우선 (필수)

| ID | 시나리오 | 기대 |
|----|----------|------|
| UT-A-20 | 차단 국가 번호가 CallRule.whitelist에 있음 | block=false |
| UT-A-21 | 화이트리스트 미일치 + 차단 국가 | block=true |
| UT-A-22 | 화이트리스트만 있고 국가 제한 없음 | block=false |

### 4.4 규칙 버전 · 캐시 (필수)

| ID | 시나리오 | 기대 |
|----|----------|------|
| UT-A-30 | remote.version > cached.version | 캐시 갱신 |
| UT-A-31 | remote.version == cached | 불필요 쓰기 스킵(또는 no-op) |
| UT-A-32 | remote 실패 | 기존 캐시 반환, 예외로 프로세스 죽지 않음 |
| UT-A-33 | 캐시 없음 + 원격 실패 | 안전한 빈/널 정책(명시: **차단 안 함** 또는 마지막 성공본 — 구현 시 **차단 안 함**으로 고정) |

### 4.5 AppScanner 점수 (필수)

| ID | 조건 | 기대 |
|----|------|------|
| UT-A-40 | installer=`com.android.vending`, 위험권한 없음 | 낮은 점수 / suspicious 아님 |
| UT-A-41 | installer=null | 위험도 상승 |
| UT-A-42 | installer≠vending + READ_SMS 등 | high / 보고 대상 |
| UT-A-43 | BIND_ACCESSIBILITY_SERVICE 포함 | 고위험 가산 |
| UT-A-44 | 시스템/자기 앱 패키지 필터 | 보고 목록 제외(정책 명시 후) |

---

## 5. Backend — 단위 · API 테스트

### 5.1 모델 · 버전 불변조건 (필수)

| ID | 시나리오 | 기대 |
|----|----------|------|
| UT-B-01 | CountryRestriction 생성 | version=1, countries는 list |
| UT-B-02 | PUT로 countries 변경 | version += 1, RuleBundle.version 반영 |
| UT-B-03 | enabled 토글만 | version += 1 |
| UT-B-04 | countries에 단일 문자열 투입 시도 | 422 또는 정규화 실패 (배열만 허용) |
| UT-B-05 | 빈 countries + enabled=true | 거부(422) 또는 no-op 정책 — **422로 고정** |
| UT-B-06 | 롤백 API | 과거 스냅샷 내용으로 **새 version** 발행, 이력 유지 |

### 5.2 Admin API (필수)

| ID | 엔드포인트 | 기대 |
|----|------------|------|
| UT-B-10 | POST `/admin/country-restrictions` | 201, 다중 countries 저장 |
| UT-B-11 | GET list | 생성분 포함 |
| UT-B-12 | PUT `{id}` | 필드 갱신+version |
| UT-B-13 | DELETE `{id}` | 204, latest 번들에서 제외 |
| UT-B-14 | GET `/admin/countries` | CN/RU/KP 등 code·callingCode |
| UT-B-15 | Admin Key 없음/오류 | 401/403 |
| UT-B-16 | Device Key로 admin 호출 | 403 |

### 5.3 Device API (필수)

| ID | 엔드포인트 | 기대 |
|----|------------|------|
| UT-B-20 | GET `/rules/latest` | RuleBundle JSON, version |
| UT-B-21 | 규칙 변경 후 latest | version 증가·내용 반영 |
| UT-B-22 | POST heartbeat | 200, lastSync 갱신 |
| UT-B-23 | POST scan-result | suspiciousApps 저장/조회 가능 |
| UT-B-24 | Device Key 없음 | 401 |
| UT-B-25 | Admin Key로 device 전용 필수 동작 | 정책: 허용 또는 403 — **device 전용은 device key만**으로 고정 |

---

## 6. 테스트 데이터 픽스처 (공통)

```json
{
  "countryRestrictions": [
    {
      "id": "cr-1",
      "name": "고위험",
      "countries": ["CN", "RU", "KP", "IR"],
      "applyTo": ["call", "dns"],
      "enabled": true,
      "version": 3
    }
  ],
  "callRules": [
    {
      "id": "call-1",
      "countryCodes": ["+86", "+7"],
      "whitelist": ["+821011112222"],
      "enabled": true,
      "version": 1
    }
  ],
  "appRiskRules": [
    {
      "id": "ar-1",
      "riskLevel": "high",
      "conditions": {
        "installerNotPlayStore": true,
        "dangerousPermissions": [
          "READ_SMS",
          "RECEIVE_SMS",
          "BIND_ACCESSIBILITY_SERVICE"
        ]
      },
      "enabled": true
    }
  ]
}
```

전화번호 픽스처는 **가상 번호만** 사용. 실번호·개인정보 금지.

---

## 7. 케이스 작성 템플릿 (TDD)

각 필수 ID마다:

1. **Red**: 실패 테스트 추가 (이름 = ID 또는 ID 주석)
2. 실행 확인 (실패 메시지 의도 일치)
3. **Green**: 최소 구현
4. 전체 관련 스위트 Pass
5. 리뷰 게이트(`02` 문서 Diff 체크리스트)

예시 이름:
- Android: `shouldBlockCall_UT_A_01_e164_cn_is_blocked`
- Backend: `test_ut_b_02_put_increments_version`

---

## 8. 추적표 (설계 §8 매핑)

| 설계 체크리스트 | 본 문서 |
|-----------------|--------|
| 국가코드 정규화 및 매칭 | UT-A-01–09 |
| 다중 국가 리스트 매칭 | UT-A-10–13 |
| 화이트리스트 우선순위 | UT-A-20–22 |
| 규칙 버전 비교 로직 | UT-A-30–33, UT-B-01–06 |
| 실기기 항목 | 단위테스트 범위 밖 → M5 |

구현 진행 시 이 섹션에 Pass/Fail 날짜를 기입해 갱신한다.

---

## 9. 보고 · 유지

- 신규 매칭 분기·API 필드 추가 시 **같은 PR에 테스트 ID 추가**가 기본
- flaky 테스트는 즉시 격리·수정 (실기기 의존을 단위로 끌어오지 말 것)
- 분기마다 §8 추적표 업데이트

---

## 10. 승인 후 첫 구현 슬라이스 (권장)

1. Backend: UT-B-01–06 + 모델 (Grok, TDD)  
2. Android: UT-A-01–13 matcher만 먼저 (앱 골격 전에도 JVM 모듈 가능)
