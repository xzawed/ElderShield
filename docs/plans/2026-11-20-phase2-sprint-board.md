# Phase 2 Sprint Board (C → A)

> Thin board — Status only. Spec: [`../specs/2026-11-20-phase2-ac-depth-quality-design.md`](../specs/2026-11-20-phase2-ac-depth-quality-design.md)

**Accepted:** 2026-11-20 · A+C · C first · popup = P3  
**Landed on `main`:** PR [#2](https://github.com/xzawed/ElderShield/pull/2) → [#3](https://github.com/xzawed/ElderShield/pull/3) → [#4](https://github.com/xzawed/ElderShield/pull/4) (merge `c86cde5`)  
**No auto-commit.** B / P4 / VpnService / SMS listener = out of scope.

## Gates

| Gate | DoD | Status |
|------|-----|--------|
| **Spec** | Phase 2 addendum + roadmap | Pass 2026-11-20 (#2) |
| **C1** | Health fields + API + admin device detail | Pass 2026-11-20 (#3) |
| **C2** | Overlay/a11y capability scoring + reasons[] | Pass 2026-11-20 (#3/#4) |
| **C3** | Threat-host feed merge + NextDNS | Pass 2026-11-20 (#3) |
| **C4** | role_lost admin surface (peers required) | Pass 2026-11-20 (#3) |
| **C-reg** | pytest + `:core:test` | Pass 2026-11-20 (53 pytest; `:core:test`; CI green) |
| **A1–A5** | Audit → notify → metrics → auth/rate-limit → backup + key rotation runbook | Pass 2026-11-20 (#2/#3) |

## Operator residual

- Replace `.example` threat hosts before production NextDNS sync
- Set `ADMIN_NOTIFY_WEBHOOK_URL` / `NEXTDNS_*` as needed
- Lab device smoke (S22 banks / nocall) when convenient
- Public repo visibility still operator choice

## Notes

- Fail-open EmptyNoBlock unchanged
- ElderShield must not use Overlay / Accessibility / Device Admin
