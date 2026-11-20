# Phase 2 Sprint Board (C → A)

> Thin board — Status only. Spec: [`../specs/2026-11-20-phase2-ac-depth-quality-design.md`](../specs/2026-11-20-phase2-ac-depth-quality-design.md)

**Accepted:** 2026-11-20 · A+C · C first · popup = P3  
**No auto-commit.** B / P4 / VpnService / SMS listener = out of scope.

## Gates

| Gate | DoD | Status |
|------|-----|--------|
| **Spec** | Phase 2 addendum + roadmap | Pass 2026-11-20 |
| **C1** | Health fields + API + admin device detail | Pass 2026-11-20 |
| **C2** | Overlay/a11y capability scoring + reasons[] | Pass 2026-11-20 |
| **C3** | Threat-host feed merge + NextDNS | Pass 2026-11-20 |
| **C4** | role_lost admin surface | Pass 2026-11-20 |
| **C-reg** | pytest + `:core:test` | Pass 2026-11-20 (53 pytest; `:core:test`) |
| **A1–A5** | Audit → notify → metrics → auth → backup runbook | Pass 2026-11-20 |

## Notes

- Fail-open EmptyNoBlock unchanged
- ElderShield must not use Overlay / Accessibility / Device Admin
- Lab device smoke (S22 banks / nocall) = operator when convenient
