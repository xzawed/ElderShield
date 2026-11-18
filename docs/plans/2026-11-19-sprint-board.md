# Phase 1 Sprint Board (Hybrid C)

> **Gate = week sprint (S0–S6). Work = short slices (½–1 day).**  
> Do not duplicate WBS/UT tables — link SSOT only. Keep this file lean.

**Accepted:** 2026-11-19 · Hybrid C  
**SSOT:** [schedule-wbs](2026-11-19-phase1-schedule-wbs.md) · [dev-review](2026-11-19-development-plan-and-review.md) · [unit-test-design](../specs/2026-11-19-unit-test-design.md) · [system-design](../specs/2026-11-18-eldershield-system-design.md)

## Roles

| Role | Duty |
|------|------|
| Grok | Implement + write failing/passing tests (primary) |
| Orchestrator | Route, hard-constraints, **re-run** `pytest` / `gradlew test`, diff review |
| User | Device checks, PR merge, commits when requested |

**No auto-commit.** Trust summaries only after local re-measure.

## TDD (every slice)

1. Add **only** the UT IDs for that slice → Red  
2. Minimal code → Green  
3. Grok verify / delegate → Orchestrator **re-runs same command**  
4. Update **Status** column below (date + Pass/Fail) — no new essay docs

## Sprint gates

| Sprint | DoD (see schedule M*) | TDD focus (IDs) | Measure | Status |
|--------|----------------------|-----------------|---------|--------|
| **S0** | Docs/rules fixed | — | Link/scope check | Pass 2026-11-19 |
| **S1** | Backend models + admin CRUD | UT-B-01–06, 10–16 | `pytest -q` | Pending |
| **S2** | Device API + min admin UI | UT-B-20–25 + version→latest smoke | `pytest -q` | Pending |
| **S3** | Android Room + sync | UT-A-30–33 | `./gradlew test` | Pending |
| **S4** | Matcher + CallScreening | UT-A-01–22 | `./gradlew test` | Pending |
| **S5** | Scanner + DnsMonitor | UT-A-40–44 | `./gradlew test` + no parent UI | Pending |
| **S6** | Device + internal ship | M5 checklist; unit only if gap | User device + 1p runbook | Pending |

## S1 slices (next)

| Slice | Deliverable | UT first |
|-------|-------------|----------|
| S1.1 | FastAPI/SQLModel/Alembic scaffold | — (scaffold; tests wire-up) |
| S1.2 | Domain version + `countries[]` invariants | UT-B-01–06 |
| S1.3 | Admin country-restrictions + countries + auth | UT-B-10–16 |

## Doc budget

- This board ≤ ~80 lines; **no** copy of UT matrices  
- Updates = Status cell only  
- New long specs only if contract changes (edit SSOT, not a twin file)
