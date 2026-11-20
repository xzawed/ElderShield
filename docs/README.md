# ElderShield 문서

Grok Build 문서 관례를 따른다.

| 영역 | 역할 |
|------|------|
| `docs/NN-*.md` | 안정적인 제품·아키텍처·로드맵 요약 |
| `docs/specs/` | **결정 근거** (설계 SSOT, 테스트 설계) |
| `docs/plans/` | **구현 서사** (일정·WBS, 기획·검토) |
| `docs/runbooks/` | 운영 절차 |
| `docs/releases/` | 릴리스 노트 |

루트: [`../README.md`](../README.md) · [`../README.ko.md`](../README.ko.md) · [`../CONTRIBUTING.md`](../CONTRIBUTING.md) · [`../SECURITY.md`](../SECURITY.md)  
에이전트 규칙: [`../AGENTS.md`](../AGENTS.md)

---

## 번호 문서 (요약)

| 문서 | 내용 |
|------|------|
| [00-product-overview.md](00-product-overview.md) | 제품 개요·하드 제약 |
| [01-architecture.md](01-architecture.md) | 아키텍처·모델·API 요약 |
| [06-roadmap.md](06-roadmap.md) | 마일스톤·Phase 로드맵 |

## specs/ (설계·결정)

| 문서 | 내용 |
|------|------|
| [2026-11-18-eldershield-system-design.md](specs/2026-11-18-eldershield-system-design.md) | 시스템 상세 설계 **SSOT** |
| [2026-11-20-phase2-ac-depth-quality-design.md](specs/2026-11-20-phase2-ac-depth-quality-design.md) | Phase 2 A+C (C→A) 설계 addendum |
| [2026-11-19-unit-test-design.md](specs/2026-11-19-unit-test-design.md) | 단위 테스트 설계·케이스 ID |

## plans/ (구현 서사)

| 문서 | 내용 |
|------|------|
| [2026-11-19-sprint-board.md](plans/2026-11-19-sprint-board.md) | Phase 1 Sprint 게이트·TDD·실측 (얇은 보드) |
| [2026-11-20-phase2-sprint-board.md](plans/2026-11-20-phase2-sprint-board.md) | Phase 2 C→A 스프린트 보드 |
| [2026-11-19-phase1-schedule-wbs.md](plans/2026-11-19-phase1-schedule-wbs.md) | Phase 1 일정·WBS |
| [2026-11-19-development-plan-and-review.md](plans/2026-11-19-development-plan-and-review.md) | 개발 기획·검토 게이트 |

## 기타

| 경로 | 내용 |
|------|------|
| [runbooks/](runbooks/README.md) | 운영 런북 (롤백 · API 키 · Admin UI · 실기기) |
| [releases/](releases/README.md) | 릴리스 노트 (M6~) |

**작성·재배치**: 2026-11-19 · **실행**: Grok 주 구현 / 오케스트레이터 리뷰 · 자동 커밋 없음
