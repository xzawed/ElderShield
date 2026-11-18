# ElderShield 시스템 상세 설계 문서

> **SSOT (Single Source of Truth)** — Grok Build `docs/specs/` 관례.  
> 이전 경로 `ElderShield_Design_v1.0.md`는 루트 스텁으로만 유지한다.

**Version**: 1.0  
**작성일**: 2026-11-18  
**서비스명**: ElderShield (실버실드)  
**대상**: Cursor 기반 구현 (WBS + TDD)  
**목적**: 부모님 Android 기기용 방어적 Guard 시스템 (전화 + 인터넷 국가 제한 + 사기앱 탐지)

---

## 1. 개요 및 하드 제약

### 1.1 서비스 개요
**ElderShield**는 기술 지식이 없는 부모님의 Android 기기(스마트폰·태블릿)를 대상으로, 위험 국가 전화·인터넷 접근을 차단하고 출처 불명/사기 앱을 탐지하는 방어적 보호 시스템입니다.  
관리자(본인)만 웹 대시보드로 규칙을 제어하며, 부모님은 설치 후 추가 조작이 필요 없습니다.

### 1.2 목적
- 위험 국가 전화·인터넷 접근 차단
- 이미 설치된 출처 불명/사기 앱 탐지 및 관리자 보고
- 관리자 전용 웹 대시보드 제어
- Bitdefender와 병행 사용 (1차 방어 역할)

### 1.3 하드 제약 (반드시 준수)
| 제약 | 상세 |
|------|------|
| 부모님 불편 제로 | 설치·권한 허용 후 추가 조작 없음. 알림/팝업 최소화 |
| 은행 앱 호환 | VpnService 기본 비활성화. Overlay/Accessibility/Device Admin 사용 금지 |
| 무인지 업데이트 | 규칙 변경·앱 업데이트 시 부모님 화면에 아무것도 표시하지 않음 |
| 합법적 방어만 | 역공격, 강제 삭제, 불법 행위 없음 |
| 리소스 최소 | 배터리 영향 최소화, WorkManager 제약 준수 |
| 다중 국가 유지 | 제한 국가 리스트는 다중 선택 가능하고 지속적으로 유지·관리 가능 |

### 1.4 대상 기기
- 부모님: Galaxy Note 10+ (Android 12 기준), Galaxy Tab S5e / Tab 6
- 테스트: Galaxy S22 Ultra, Galaxy Tab 6
- minSdk: 29 (Android 10)

---

## 2. 전체 아키텍처

```
[ElderShield 관리자 웹 대시보드] 
        │ HTTPS + API Key
        ▼
[ElderShield Backend (FastAPI 권장)]
  - 규칙 저장 (버전 관리)
  - 기기 등록/상태
  - 앱 스캔 결과 수신
        │ 주기적 Pull (WorkManager)
        ▼
[ElderShield Android App]
  - CallScreeningService
  - RuleSyncWorker
  - AppScanner
  - DnsMonitor (상태 확인)
  - Room 로컬 캐시
```

**인터넷 차단 전략**: Private DNS (NextDNS 또는 AdGuard) 중심.  
로컬 VpnService는 Phase 후반 옵션 (은행 앱 테스트 후 결정).

---

## 3. 데이터 모델

### 3.1 CountryRestriction (핵심)

```json
{
  "id": "uuid",
  "name": "고위험 국가 그룹",
  "countries": ["CN", "RU", "KP", "IR"],          // ISO 3166-1 alpha-2, 다중
  "applyTo": ["call", "dns"],                     // 적용 범위
  "enabled": true,
  "version": 3,
  "description": "중국, 러시아 등",
  "createdAt": "2026-11-18T00:00:00Z",
  "updatedAt": "2026-11-18T00:00:00Z"
}
```

- 여러 개의 CountryRestriction 그룹 생성 가능
- `countries`는 항상 배열 (다중 선택 유지)
- `applyTo` 값: `"call"` | `"dns"` | `"internet"` (현재는 call + dns 중심)

### 3.2 CallRule (보조)
```json
{
  "id": "uuid",
  "countryCodes": ["+86", "+7"],                  // 전화 국가코드
  "numberPatterns": ["+86*"],                     // 선택적 패턴
  "whitelist": ["+8210xxxxxxxx"],
  "enabled": true,
  "version": 1
}
```

### 3.3 AppRiskRule
```json
{
  "id": "uuid",
  "riskLevel": "high",
  "conditions": {
    "installerNotPlayStore": true,
    "dangerousPermissions": ["READ_SMS", "RECEIVE_SMS", "BIND_ACCESSIBILITY_SERVICE"]
  },
  "enabled": true
}
```

### 3.4 Device
```json
{
  "id": "uuid",
  "deviceUuid": "앱에서 생성한 UUID",
  "name": "아빠 폰",
  "model": "SM-N975N",
  "lastSyncAt": "...",
  "appVersion": "1.0.0",
  "dnsConfigured": true,
  "callScreeningEnabled": true
}
```

### 3.5 RuleBundle (동기화 단위)
앱이 한 번에 받아가는 단위:
```json
{
  "version": 5,
  "countryRestrictions": [ ... ],
  "callRules": [ ... ],
  "appRiskRules": [ ... ],
  "updatedAt": "..."
}
```

---

## 4. API 스펙

**Base URL**: `https://your-backend.example.com/api/v1`  
**인증**: `X-API-Key: <device_or_admin_key>` (기기용 / 관리자용 분리 권장)

### 4.1 기기용 API

#### GET `/rules/latest`
최신 규칙 번들 조회
```http
GET /rules/latest
X-API-Key: device-key
```
**Response 200**:
```json
{
  "version": 5,
  "countryRestrictions": [...],
  "callRules": [...],
  "appRiskRules": [...],
  "updatedAt": "2026-11-18T12:00:00Z"
}
```

#### POST `/devices/heartbeat`
기기 상태 보고
```json
{
  "deviceUuid": "...",
  "appVersion": "1.0.0",
  "dnsConfigured": true,
  "callScreeningEnabled": true,
  "lastRuleVersion": 5
}
```

#### POST `/devices/apps/scan-result`
사기앱 스캔 결과 보고
```json
{
  "deviceUuid": "...",
  "suspiciousApps": [
    {
      "packageName": "com.fake.app",
      "installer": null,
      "dangerousPermissions": ["READ_SMS"],
      "riskScore": 85
    }
  ]
}
```

### 4.2 관리자용 API

#### GET `/admin/country-restrictions`
목록 조회

#### POST `/admin/country-restrictions`
생성
```json
{
  "name": "고위험 국가",
  "countries": ["CN", "RU", "KP"],
  "applyTo": ["call", "dns"],
  "enabled": true,
  "description": "..."
}
```

#### PUT `/admin/country-restrictions/{id}`
수정 (버전 자동 증가)

#### DELETE `/admin/country-restrictions/{id}`
삭제

#### GET `/admin/countries`
국가 마스터 리스트 (다중 선택 UI용)
```json
[
  {"code": "CN", "name": "중국", "callingCode": "+86"},
  {"code": "RU", "name": "러시아", "callingCode": "+7"},
  {"code": "KP", "name": "북한", "callingCode": "+850"}
]
```

#### GET `/admin/devices`
등록된 기기 목록 + 상태

#### POST `/admin/rules/rollback`
특정 버전으로 롤백

---

## 5. Android 모듈 설계 (Cursor 구현 기준)

### 5.1 패키지 구조 제안
```
com.eldershield
├── data
│   ├── local (Room)
│   ├── remote
│   └── repository
├── domain
│   ├── model
│   └── usecase
├── service
│   ├── CallScreeningService
│   └── RuleSyncWorker
├── scanner
│   └── AppScanner
└── ui (최소, 관리자 테스트용)
```

### 5.2 핵심 인터페이스

```kotlin
interface RuleRepository {
    suspend fun getLatestRules(): RuleBundle
    suspend fun getCachedRules(): RuleBundle?
    suspend fun saveRules(bundle: RuleBundle)
}

interface CountryRestrictionMatcher {
    fun shouldBlockCall(phoneNumber: String, rules: List<CountryRestriction>): Boolean
    fun getRestrictedCountries(rules: List<CountryRestriction>): Set<String>
}

interface AppScanner {
    suspend fun scanInstalledApps(): List<SuspiciousApp>
}
```

### 5.3 CallScreeningService 동작
- `onScreenCall()`에서 국가코드 추출
- 로컬 캐시된 `CountryRestriction`의 `countries`와 매칭
- 매칭 시 `CallResponse.Builder().setDisallowCall(true).setRejectCall(true)`
- 알림은 최소화 또는 없음

### 5.4 동기화 (RuleSyncWorker)
- WorkManager PeriodicWork (15분~1시간 간격, 배터리 제약 고려)
- 네트워크 없을 경우 기존 캐시 유지
- 실패해도 크래시 없이 종료
- 부모님 화면에 어떤 UI도 표시하지 않음

### 5.5 AppScanner
- `PackageManager.getInstalledPackages()`
- installer가 `com.android.vending`이 아니거나 null인 경우 위험도 상승
- 위험 권한 조합 체크
- 결과는 서버로만 전송 (로컬 알림 없음)

---

## 6. 국가 제한 상세 로직

### 6.1 전화 차단
- 전화번호에서 국가코드 추출 (`+86`, `0086`, `86` 등 정규화)
- `CountryRestriction` 중 `applyTo`에 `"call"` 포함 + `enabled=true`인 항목의 `countries`와 매칭
- 화이트리스트 우선 적용

### 6.2 DNS / 인터넷 차단
- 서버에서 제한 국가의 ccTLD + 주요 도메인 리스트를 생성하거나
- NextDNS/AdGuard에 규칙 동기화 (권장: 초기에는 수동 또는 API 연동)
- 앱은 Private DNS 설정 상태만 모니터링하고, 잘못되면 관리자에게만 보고

### 6.3 다중 선택 유지
- DB에 `countries`를 JSON 배열 또는 별도 테이블로 저장
- 관리 웹에서 멀티 셀렉트 컴포넌트 사용
- 변경 시 `version` 자동 증가 → 앱이 다음 동기화 시 반영

---

## 7. 보안 및 운영

- 기기 API Key와 관리자 API Key 분리
- HTTPS 필수
- 규칙 변경 이력 보관 (감사 로그)
- 민감 정보(전화번호 원문 등) 최소화 저장
- Play Store 내부 테스트 트랙으로 앱 배포 → 자동 업데이트

---

## 8. 검증 체크리스트 (TDD + 실기기)

### 단위 테스트
- [ ] 국가코드 정규화 및 매칭
- [ ] 다중 국가 리스트 매칭
- [ ] 화이트리스트 우선순위
- [ ] 규칙 버전 비교 로직

### 실기기 테스트
- [ ] S22 Ultra에서 은행 앱(토스, 카카오뱅크 등) 정상 동작
- [ ] Note 10+에서 전화 차단 동작
- [ ] 규칙 변경 후 백그라운드 반영 (화면 표시 없음)
- [ ] Private DNS 상태에서 인터넷 정상 + 제한 국가 차단
- [ ] 사기앱 스캔 결과 대시보드 표시

---

## 9. Cursor 구현 가이드

1. **Backend 먼저**: FastAPI + SQLAlchemy/SQLModel + Alembic
2. **데이터 모델** 위 스펙 그대로 구현
3. **관리자 API** + 간단한 웹 UI (HTMX 또는 Vue)
4. **Android**: 
   - 패키지명 `com.eldershield`
   - Room Entity로 RuleBundle 캐시
   - CallScreeningService
   - WorkManager
5. **TDD**: 매칭 로직부터 Red-Green-Refactor
6. **테스트 기기**: 본인 S22 Ultra → 부모님 기기

---

## 10. 향후 확장 (Phase 2+)
- VpnService 기반 IP 국가 필터 (은행 앱 테스트 후)
- NextDNS API 자동 연동
- 더 정교한 앱 위험 점수
- 통계 대시보드

---

**이 문서를 기준으로 Cursor에서 ElderShield Backend → Android 순으로 구현을 시작하세요.**  
규칙 모델과 API를 먼저 고정하면 이후 변경 비용이 최소화됩니다.
