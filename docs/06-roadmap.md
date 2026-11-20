# 06. 로드맵

**스프린트 보드 (Hybrid C)**: [`plans/2026-11-19-sprint-board.md`](plans/2026-11-19-sprint-board.md)  
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

## Phase 2 (A+C · C 먼저)

**설계 SSOT addendum**: [`specs/2026-11-20-phase2-ac-depth-quality-design.md`](specs/2026-11-20-phase2-ac-depth-quality-design.md)  
**스프린트 보드**: [`plans/2026-11-20-phase2-sprint-board.md`](plans/2026-11-20-phase2-sprint-board.md)

| 축 | 내용 |
|----|------|
| **C 보호 깊이** | Device health 신호 · 오버레이/접근성 **가능 앱** 탐지(P3) · scam-ad/phishing DNS 피드 · CallScreening **role_lost 경보만** |
| **A 운영 품질** | Audit log → Admin notify → metrics/health → auth harden → backup 런북 |
| **비범위** | B 다조직/테넌트 · P4 화면 읽기 · VpnService(후순위) · 스미싱 리스너(별도 게이트) |

Phase 1 운영자 잔여(코드 밖): NextDNS 전용 프로필·`NEXTDNS_*` · Play 내부 AAB 업로드 — [`nextdns-setup.md`](runbooks/nextdns-setup.md) · [`play-internal.md`](runbooks/play-internal.md)

## Phase 3+ (후순위)

- VpnService 기반 IP 국가 필터 (은행앱 회귀 후에만)
- 다조직·테넌트(B) — 먼 미래

## 크리티컬 패스

규칙 모델·API 계약 고정 → Android 동기화 → 전화 매칭 → 실기기 전화 차단
