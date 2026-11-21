# Incident Evidence Pack — 신고용 최소 증거 수집 설계

**상태:** Approved + implementation landed (A+B; C enrich on export).  
**일자:** 2026-11-21  
**관련 SSOT:** [`2026-11-18-eldershield-system-design.md`](2026-11-18-eldershield-system-design.md)  
**개인정보:** [`../legal/privacy-policy.md`](../legal/privacy-policy.md) 동반 개정

## 1. 목적

관리자가 **범죄예방·기관 신고**에 쓸 수 있도록, 위험 사건 발생 시 **최소 메타 증거 패킷(Incident)** 을 남긴다.

수집 축 (확정):

| 축 | 내용 |
|----|------|
| **A** | 사기앱 포렌식 (서명·APK 해시·권한·설치출처) |
| **B** | 전화 메타 (국가코드·시각·차단여부·번호 해시) |
| **C** | DNS/도메인 (NextDNS 질의·차단 로그; VpnService 없음) |

**의도적으로 불가·비범위:** 원격 범인 GPS, 상시 패킷 캡처, 전화번호 원문 서버 저장, VpnService 기본 활성, 부모님 알림/팝업.

## 2. 부모 기기 부하 한도 (§1 승인)

| 항목 | 한도 |
|------|------|
| 평소 추가 서버 전송 | 없음 (기존 sync/heartbeat/스캔 주기만) |
| 로컬 버퍼 | Room 링버퍼, 디스크 수 MB 이하 |
| 사건 업로드 | **JSON 메타만** (APK 바이너리 기본 미전송) |
| 백그라운드 | 기존 WorkManager; 신규 상시 FG 서비스·VPN·GPS 금지 |
| UX | 부모님 알림/팝업 없음 |

평소 LTE·CPU 증가는 체감 이하를 목표로 한다. 사건 시 업로드는 통상 수십 KB~소량 MB(해시·메타).

## 3. 트리거 · 윈도우 · 버퍼 (§2 승인)

### 3.1 트리거 A (하나라도 → Incident 확정)

1. 앱 스캔 `riskScore ≥ 50` (기존 `AppRiskScorer.THRESHOLD`)
2. CallScreening **Reject** (국가 제한 매칭)
3. DNS 차단 히트 (NextDNS 로그 또는 denylist 매칭 요약 — NextDNS 연동 후)

### 3.2 시간 윈도우

- 확정 시각 `T` 기준 **T−24h ~ T+1h**
- 동일 `deviceUuid`, **1시간 내** 중복 트리거 → **단일 Incident로 병합**

### 3.3 로컬 버퍼 (평소 서버 미전송)

| 버퍼 | 필드 | 상한 |
|------|------|------|
| 전화 | `at`, `direction=incoming`, `countryIso`, `decision`, `phoneHash` (SHA-256), optional `last4` | 200건 FIFO |
| 앱 | 패키지·score·reasons 요약 | 50건 |
| DNS | 기기는 기존 `dnsConfigured`/`hostClass`만; 질의 로그는 **서버가 NextDNS API pull** (기기 LTE 0) | — |

## 4. Incident 페이로드 (메타만)

```json
{
  "incidentId": "uuid",
  "deviceUuid": "uuid",
  "triggeredAt": "ISO-8601",
  "triggers": ["app_scan", "call_reject", "dns_block"],
  "window": { "from": "...", "to": "..." },
  "apps": [
    {
      "packageName": "com.example.risk",
      "signingCertSha256": "...",
      "apkSha256": "...",
      "versionName": "...",
      "versionCode": 0,
      "installer": null,
      "permissions": [],
      "reasons": [],
      "riskScore": 100,
      "firstSeenAt": "..."
    }
  ],
  "calls": [
    {
      "at": "...",
      "countryIso": "CN",
      "decision": "Reject",
      "phoneHash": "...",
      "last4": "7766"
    }
  ],
  "dns": {
    "available": false,
    "unavailableReason": "nextdns_unset",
    "events": [
      { "at": "...", "domain": "baidu.com", "action": "block" }
    ]
  },
  "countryHints": {
    "callIsoMode": "CN",
    "dnsCctldMode": "cn",
    "note": "추정 힌트이며 범인 소재 확정이 아님"
  },
  "protectionSnapshot": {
    "dnsConfigured": false,
    "dnsHostClass": "none",
    "callScreeningEnabled": true,
    "lastRuleVersion": 2,
    "protectionDegraded": true
  }
}
```

**국가 힌트:** 차단 전화 ISO 최빈값 + 차단 도메인 ccTLD 최빈값. 기관 제출 시 “추정”으로 명시.

## 5. API · 저장 (§3 승인)

### 5.1 기기

- `POST /api/v1/devices/incidents` — body = Incident JSON; 멱등 키 `incidentId`
- 인증: 기존 device `X-API-Key` / per-device token

### 5.2 관리자

- `GET /api/v1/admin/devices/{deviceUuid}/incidents`
- `GET /api/v1/admin/incidents/{incidentId}`
- `GET /api/v1/admin/incidents/{incidentId}/export` — 신고 패킷 다운로드
- Admin UI: 기기 상세에 Incident 목록 + 내보내기 버튼

### 5.3 보관

- 기본 TTL **90일** (설정 가능) 후 삭제
- admin API key만 조회/export

### 5.4 NextDNS (축 C)

- Railway `NEXTDNS_API_KEY` + `NEXTDNS_PROFILE_ID` 필수 시 C 완성
- 미설정: Incident에 `dns.available=false`, A·B만 유효
- denylist sync(`POST .../dns-denylist/sync-nextdns`)와 동일 자격 증명 재사용
- 질의 로그는 **백엔드가 사건 윈도우로 pull** 해 Incident에 병합 (부모 폰 부하 없음)

## 6. Android 구현 요지

- `CallEvidenceEntity` 링버퍼; Reject/Allow 모두 메타만 기록 (원문 번호 로그캣·서버 금지)
- `IncidentAssembler`: 트리거 시 윈도우 슬라이스 + 앱 서명/해시 계산(이미 설치된 APK 로컬 해시)
- `OneTimeWorkRequest`로 `POST .../incidents` (기존 WorkManager 제약 준수)
- GPS · VPN · Accessibility · Device Admin · Overlay **사용 금지 유지**

## 7. SSOT · 개인정보 개정 포인트

`2026-11-18-eldershield-system-design.md`에 addendum 링크:

- 민감정보 최소화 **유지**
- **예외:** 트리거 A로 확정된 Incident 메타만 서버 보관 (번호는 해시)
- Gps/상시 스트림/VpnService 기본 비활성 **불변**

`privacy-policy.md`:

- 수집 표에 Incident(앱 포렌식 해시·전화 해시 메타·NextDNS 차단 도메인 요약) 추가
- “수집하지 않음”에 GPS·번호 원문·상시 DNS 전문 유지
- 목적: 가족 관리자의 범죄예방·수사기관 신고 지원
- 보관 90일

## 8. 구현 순서 (계획 단계용 스케치)

1. Backend: `incident` 테이블 + POST/GET/export + Admin UI 목록  
2. Android: 전화 링버퍼 + Reject/스캔 트리거 + 메타 업로드 (A+B)  
3. Ops: Railway NextDNS 설정 + sync + 서버 pull로 C 보강  
4. privacy/SSOT 문구 반영 · 단위 테스트(트리거 병합·해시·멱등)

## 9. 성공 기준

- [ ] 평소 추가 서버 트래픽 0 (증거 경로)
- [ ] Reject 또는 score≥50 시 Incident 1건 생성·관리자 export 가능
- [ ] 번호 원문이 DB·export에 없음
- [ ] NextDNS 설정 시 윈도우 내 block 도메인이 Incident에 포함
- [ ] NextDNS 미설정 시 A+B만으로 export 가능, C는 unavailable 명시
- [ ] 부모님 기기 알림 없음

## 10. 자기검토 (스펙)

| 점검 | 결과 |
|------|------|
| 플레이스홀더 | 없음 (예시 JSON은 스키마 예시) |
| SSOT 충돌 | VpnService/GPS/알림 금지와 정합; “민감정보 최소화”는 사건 메타 예외로 명시 |
| 모호성 | APK 바이너리 업로드 = 기본 오프(확정). Wi‑Fi 옵션은 본 Phase 비범위 |
| 범위 | A+B 우선, C는 NextDNS 의존 — 성공 기준에 분기 명시 |
