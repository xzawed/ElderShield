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
| **S1** | Backend models + admin CRUD | UT-B-01–06, 10–16 | `pytest -q` | Pass 2026-11-19 (14 tests) |
| **S2** | Device API + min admin UI | UT-B-20–25 + version→latest smoke | `pytest -q` | Pass 2026-11-19 (22 tests) |
| **S3** | Android Room + sync | UT-A-30–33 | `./gradlew :core:test` | Pass 2026-11-19 |
| **S4** | Matcher + CallScreening | UT-A-01–22 | `./gradlew :core:test` + assembleDebug | Pass 2026-11-19 |
| **S5** | Scanner + DnsMonitor | UT-A-40–44 | `./gradlew :core:test` + assembleDebug | Pass 2026-11-19 |
| **S6** | Device + internal ship | M5 checklist; unit only if gap | User device + 1p runbook | Partial 2026-11-21 — Incident evidence pack A+B implemented, C NextDNS-dependent |

## S1 slices

| Slice | Deliverable | UT first | Status |
|-------|-------------|----------|--------|
| S1.1 | FastAPI/SQLModel/Alembic scaffold | health | Pass |
| S1.2 | Domain version + `countries[]` invariants | UT-B-01–06 | Pass |
| S1.3 | Admin country-restrictions + countries + auth | UT-B-10–16 | Pass |

## S2 slices

| Slice | Deliverable | UT first | Status |
|-------|-------------|----------|--------|
| S2.1 | Device API: rules/latest, heartbeat, scan-result | UT-B-20–25 | Pass 2026-11-19 (20 tests) |
| S2.2 | Min admin UI (multi-select countries) | UI multi-select test | Pass 2026-11-19 |

## S3 slices

| Slice | Deliverable | UT first | Status |
|-------|-------------|----------|--------|
| S3.1 | Android scaffold + Room RuleBundle cache | — | Pass (app sources; enable `:app` with SDK) |
| S3.2 | RuleSyncWorker + RuleSyncPolicy | UT-A-30–33 | Pass (`:core:test`) |

## S4 slices

| Slice | Deliverable | UT first | Status |
|-------|-------------|----------|--------|
| S4.1 | CountryRestrictionMatcher | UT-A-01–22 | Pass (`:core:test`) |
| S4.2 | CallScreeningService wire-up | assembleDebug | Pass (needs role on device) |

## S5 slices

| Slice | Deliverable | UT first | Status |
|-------|-------------|----------|--------|
| S5.1 | AppScanner risk scoring | UT-A-40–44 | Pass |
| S5.2 | DnsMonitor + DeviceReportWorker heartbeat | unit + assemble | Pass |

## S6 slices (next)

| Slice | Deliverable | Notes |
|-------|-------------|-------|
| S6.1 | Device checklist (bank apps, call block) | AVD call matrix Pass; S22 nocall Pass; human 010 optional |
| S6.2 | Play internal track + rollback runbook | Runbooks + `v0.1.0.md`; **signed AAB upload = operator** |
| S6.3 | Country internet via DNS denylist | Code Pass; denylist Pass; **NEXTDNS_* sync + .cn NXDOMAIN = operator** |
| S6.4 | CI closeout | Pass (pytest + `:core:test`) |
| S6.5 | Admin React SPA Phase A | shell+login+dashboard+devices; Railway/CI SPA build | Pass 2026-11-21 |
| S6.6 | Admin log visibility L1–L3 | Incident/device/audit/dns-logs SPA | Pass 2026-11-21 |
| S6.7 | Admin SPA shell unity | primary nav Link-only; list pages SPA; smoke nav continuity | Pass 2026-11-21 |

## Doc budget

- This board ≤ ~80 lines; **no** copy of UT matrices  
- Updates = Status cell only  
- New long specs only if contract changes (edit SSOT, not a twin file)
