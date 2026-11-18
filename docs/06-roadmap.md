# 06. 로드맵

**상세 WBS·주간 일정**: [`plans/2026-11-19-phase1-schedule-wbs.md`](plans/2026-11-19-phase1-schedule-wbs.md)  
**기획·검토 게이트**: [`plans/2026-11-19-development-plan-and-review.md`](plans/2026-11-19-development-plan-and-review.md)

## Phase 1 마일스톤 (약 6주)

| ID | 마일스톤 | 목표 |
|----|----------|------|
| M0 | 문서·규칙 고정 | AGENTS + docs 세트 |
| M1 | Backend API v1 | 규칙·기기 API + 단위테스트 |
| M2 | 관리자 최소 UI | 다중 국가·기기·스캔 조회 |
| M3 | Android 코어 | Room + Sync + CallScreening |
| M4 | 스캔·DNS 모니터 | AppScanner + heartbeat |
| M5 | 실기기 검증 | 은행앱 호환 + 전화 차단 |
| M6 | 내부 배포 | Play 내부 트랙 + 롤백 런북 |

## Phase 2+

- VpnService 기반 IP 국가 필터
- NextDNS API 자동 연동
- 정교한 앱 위험 점수·통계 대시보드

## 크리티컬 패스

규칙 모델·API 계약 고정 → Android 동기화 → 전화 매칭 → 실기기 전화 차단
