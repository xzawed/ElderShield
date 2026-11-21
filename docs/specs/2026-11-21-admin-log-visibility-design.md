# Admin 수집 로그 가시화 — 설계

**상태:** Done (PR #21) · 셸 통일 follow-up PR #22  
**일자:** 2026-11-21  
**관련:** [`2026-11-21-incident-evidence-pack-design.md`](2026-11-21-incident-evidence-pack-design.md), [`2026-11-21-admin-react-spa-dashboard-design.md`](2026-11-21-admin-react-spa-dashboard-design.md)  
**계획:** [`../plans/2026-11-21-admin-log-visibility-implementation.md`](../plans/2026-11-21-admin-log-visibility-implementation.md)

## 1. 목적

관리자가 수집된 Incident·기기 health/스캔·audit·NextDNS 질의 로그를 **JSON 원문 없이** 요약·도표·타임라인으로 읽는다.

## 2. 확정

| 항목 | 결정 |
|------|------|
| 범위 | **C** — Incident + health/스캔/audit + NextDNS 로그 |
| 순서 | Incident 상세 → 기기/audit → NextDNS 전용 |
| 방식 | SPA + Recharts (안1); 기존 JSON export 유지 |
| 비범위 | 서버 PDF/인쇄 HTML, Grafana, GPS·원문 번호 |

## 3. 라우트 · API

| 화면 | SPA 경로 | API |
|------|----------|-----|
| Incident 상세 | `/admin/ui/incidents/:id` | `GET /api/v1/admin/incidents/{id}/export` |
| 기기 상세 | `/admin/ui/devices/:uuid` | `GET /api/v1/admin/devices/{uuid}` |
| Audit | `/admin/ui/audit` | `GET /api/v1/admin/audit` |
| NextDNS 로그 | `/admin/ui/dns-logs` | `GET /api/v1/admin/dns-logs` (신규) |

인증: 세션 쿠키 + `X-ElderShield-Admin: 1`.

## 4. Incident 상세 (L1)

1. 요약 띠 — triggers, triggeredAt, window, countryHints, protectionSnapshot  
2. 타임라인 — calls / apps / dns.events 시각 순 병합  
3. 앱·전화 표 (해시·phoneHash 접기; **원문 번호 금지**)  
4. DNS Top-N 막대 + 이벤트 표; unset 시 안내  
5. JSON 다운로드 + 기기 상세 링크  

대시보드 ThreatTable 행 → Incident 상세.

## 5. 기기 · Audit (L2)

- DeviceDetail: KPI 미니 + healthEvents + scans + incidents 링크  
- AuditPage: Jinja audit 대체 SPA, 클라이언트 필터  

## 6. NextDNS 로그 (L3)

`GET /api/v1/admin/dns-logs?from=&to=&status=blocked&limit=`

- 미설정: **503** `{ "error": "nextdns_unset" }`  
- 성공: `{ "events": [{ "at", "domain", "status" }], "nextCursor"? }`  
- denylist(정책)와 분리 — dns-logs는 관측만  

## 7. 자기검토

| 점검 | 결과 |
|------|------|
| SSOT | 증거 패킷·개인정보(해시만) 준수 |
| SPA Phase A | 셸·쿠키 CSRF 재사용 |
| 셸 통일 | dns-logs/audit는 SPA nav; 타 목록 Jinja 링크 금지(설계 §2) |
| 플레이스홀더 | L1/L2/L3 완료 |
