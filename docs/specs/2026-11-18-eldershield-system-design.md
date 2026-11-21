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

#### 1.2.1 Bitdefender / CallScreening 병행 정책 (권장안 A · 확정)

Android는 `ROLE_CALL_SCREENING`을 **앱 하나만** 부여한다. ElderShield와 Bitdefender(또는 Samsung Smart Call 등)가 **동시에** 수신 스크리닝할 수는 없다.

| 규칙 | 내용 |
|------|------|
| 병행 의미 | Bitdefender는 악성코드·일반 스팸 등 **1차 방어**로 유지. ElderShield는 DNS/스캔 + **역할 보유 시에만** 국가 전화 차단 |
| 가로채기 금지 | 역할이 비어 있지 않으면 `adb`/프로비저닝으로 **강탈하지 않음**. 부모님에게 Bitdefender를 끄라고 **지시하지 않음** |
| 역할 미보유 시 | 국가 **전화** 차단은 비활성(`callScreeningEnabled=false`). DNS·앱 스캔·heartbeat는 정상 동작 |
| 관리자 보고 | heartbeat에 역할 보유 여부 + (가능하면) 다른 CallScreening 구현 패키지 힌트. “BD를 제거하라” UI 금지 |
| 역할 요청 UI | 다른 CallScreening 앱이 설치된 채 미보유면 **자동 요청하지 않음**. 관리자가 명시 탭할 때만 시스템 전환 UI(취소 가능) |

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

**`version` (bundle generation)**: 제한 그룹·CallRule의 **내용 변경(생성/수정/삭제/롤백)마다 단조 증가**하는 동기화 키다.  
개별 `CountryRestriction.version` / `CallRule.version`의 `max`가 아니다. 기기는 `remote.version > cached.version`일 때만 캐시를 갱신한다.

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
등록된 기기 목록 + 상태 (`deviceUuid`, `appVersion`, `dnsConfigured`, `callScreeningEnabled`, `lastRuleVersion`, `lastSyncAt`, …)

#### GET `/admin/call-rules` / POST `/admin/call-rules`
CallRule(화이트리스트) 목록·생성. 생성 시 RuleBundle generation 증가.
```json
{ "countryCodes": ["+86"], "whitelist": ["+8613812345678"], "enabled": true }
```

#### POST `/admin/rules/rollback`
특정 **restriction 스냅샷**을 새 row version으로 발행하고 RuleBundle generation을 올린다.
```json
{ "restrictionId": "<uuid>", "targetVersion": 1 }
```
응답에 `bundleVersion` 포함. 상세: [`../runbooks/rollback.md`](../runbooks/rollback.md)

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
- **전제:** ElderShield가 `ROLE_CALL_SCREENING`을 보유할 때만 플랫폼이 이 서비스를 호출한다. 미보유(Bitdefender 등이 보유)면 §1.2.1에 따라 전화 경로는 비활성 — 병행 위반이 아님

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
- **수신만** 국가 차단 (`Call.Details.DIRECTION_INCOMING`).  
  플랫폼은 발신에도 `CallScreeningService`를 호출할 수 있으나(발신자 표시용), ElderShield는 **발신(DIRECTION_OUTGOING)에 대해 국가 차단하지 않는다**.
- 번호 정규화 → 국제 숫자열(E.164 digits, `+` 없음):
  - `+86…` / `0086…` / `86…` (이미 국제형)
  - **기기 기본 지역(Phase 1: KR)**: 국내 트렁크 `0…`(예: `010…`) → `82…`로 변환 후 매칭
  - 화이트리스트 비교도 **동일 정규화** 후 전체 숫자 일치만 허용 (접두 `+86` 단독 금지)
- `CountryRestriction` 중 `applyTo`에 `"call"` 포함 + `enabled=true`인 항목의 `countries`(ISO) ↔ calling code 접두 매칭
- 화이트리스트(`CallRule.whitelist`) 우선. `countryCodes` / `numberPatterns`는 Phase 1에서 **차단에 미사용**(예약·표시용)

### 6.2 DNS / 인터넷 차단 (중요 · Private DNS 경로)

은행 앱 호환을 위해 **VpnService 기본 비활성**을 유지한다. 국가 인터넷 차단의 **1차 구현 경로**는 Private DNS(NextDNS 권장, AdGuard 가능)이다.

| 계층 | 역할 |
|------|------|
| Backend | `applyTo`에 `dns` 또는 `internet`이 있는 enabled `CountryRestriction` → **denylist**(ccTLD + 국가별 주요 도메인) 생성 |
| Admin | denylist 조회·복사(NextDNS/AdGuard에 반영). 이후 **NextDNS API 자동 푸시** |
| Android 앱 | 트래픽을 직접 차단하지 않음. Private DNS **hostname + 허용 리졸버** 여부를 `dnsConfigured`로 보고 |

- `applyTo: call` → CallScreening만. `dns`/`internet` → denylist/DNS 정책만 (전화와 독립).
- 한계(정직하게): IP 직결·DoH 우회·앱 내장 DNS는 Private DNS만으로 100% 불가. 심층 차단은 Phase 후반 VpnService **옵션**(은행 앱 회귀 후).
- `dnsConfigured=true`: Private DNS **hostname** 모드 + specifier가 허용 호스트와 **일치/하위 도메인** (부분 문자열 삽입 금지)

### 6.2.1 권장 구현 (사실 검증 2026-11-19)

| 후보 | 판정 | 이유 |
|------|------|------|
| **NextDNS + Android Private DNS** | **채택** | SSOT·은행앱(VPN 없음)·LTE에서도 hostname만 설정. 공식 API로 `security.tlds`(cn/ru…) + `denylist` 호스트 동기화 가능 ([NextDNS API](https://nextdns.github.io/api/)) |
| AdGuard Home 자가호스팅 | 비권장(1차) | Private DNS용 공인 인증서·상시 서버 필요, 부모 LTE에서 불리 |
| 앱 VpnService 국가 IP 필터 | 후순위 | 하드 제약(은행 앱). 회귀 통과 후에만 옵션 |
| denylist에 `*.cn` 문자열 | **폐기** | API는 TLD 차단을 `security.tlds`의 `cn`으로 제공. `*.cn` denylist는 비공식·오류 위험 |

한계(정직): DNS 계층은 geo-IP가 아님. DoH 우회는 NextDNS Parental Control **Block bypass methods**로 완화. 하드코드 DNS·별도 VPN은 막지 못함.

### 6.2.2 API (관리자)
- `GET /api/v1/admin/dns-denylist` — `{ countries, tlds, domains }`
- `POST /api/v1/admin/dns-denylist/sync-nextdns` — `NEXTDNS_API_KEY` + `NEXTDNS_PROFILE_ID`(전용 프로필 권장). 미설정 시 503

### 6.3 다중 선택 유지
- DB에 `countries`를 JSON 배열 또는 별도 테이블로 저장
- 관리 웹에서 멀티 셀렉트 컴포넌트 사용
- 변경 시 **RuleBundle generation** 및 해당 행 `version` 증가 → 앱이 다음 동기화 시 반영

### 6.4 Private DNS 상태 (`dnsConfigured`)
- Private DNS **hostname** 모드이면서 specifier가 **허용 호스트**(NextDNS/AdGuard 등)와 일치할 때만 `true`
- 임의 Private DNS hostname은 보호 성공으로 보지 않음

---

## 7. 보안 및 운영

- 기기 API Key와 관리자 API Key 분리 (`change-me-*` 기본값은 기동 거부; 로컬만 `ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1`)
- HTTPS 필수. Admin UI 쿠키는 **HMAC 세션 토큰**(API 키 원문 금지). 운영 HTTPS에서는 `COOKIE_SECURE=1`
- 규칙 변경 이력 보관 (restriction version 스냅샷 + 롤백)
- 민감 정보(전화번호 원문 등) 최소화 저장
- **Incident 증거 패킷** (트리거 확정 시에만): 앱·전화·DNS **메타만** 서버 보관. 전화번호 원문 없음(해시만). GPS·VpnService 없음. 보관 TTL **90일**. 상세 [`2026-11-21-incident-evidence-pack-design.md`](2026-11-21-incident-evidence-pack-design.md)
- Play Store 내부 테스트 트랙으로 앱 배포 → 자동 업데이트
- 원격 규칙 sync 실패 시 기기는 캐시/EmptyNoBlock(차단 안 함)을 유지하되 WorkManager는 **retry**

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

## 10. 향후 확장
- **Phase 2 (A+C)** — 구현됨: [`2026-11-20-phase2-ac-depth-quality-design.md`](2026-11-20-phase2-ac-depth-quality-design.md) (health · P3 overlay capability · threat DNS · audit/notify). NextDNS API 푸시는 Phase 1 경로에 포함.
- VpnService 기반 IP 국가 필터 (은행 앱 회귀 통과 후에만 옵션)
- B 다조직/테넌트 · P4 화면 읽기 · 스미싱 리스너 (별도 게이트)
- 더 정교한 통계 대시보드

---

**이 문서를 기준으로 Cursor에서 ElderShield Backend → Android 순으로 구현을 시작하세요.**  
규칙 모델과 API를 먼저 고정하면 이후 변경 비용이 최소화됩니다.
