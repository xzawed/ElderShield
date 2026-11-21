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

| Item | Status |
|------|--------|
| NextDNS sync (`NEXTDNS_*`) | Pass 2026-11-20 — denylist stable (country + curated local threats); `*.example` excluded; 429 backoff |
| Threat hosts local overlay | Pass 2026-11-20 — `threat_hosts.local.json` (gitignored) from PhishDestroy primary_active, brand-FP filtered, capped |
| Play signed AAB | Pass build 2026-11-20 — local `upload-keystore.jks` + `app-release.aab` (gitignored). **Play Console upload** still needs Google login |
| Zero-touch enroll (spec+impl) | **Code ready 2026-11-20** (#9) — enrollment window · per-device token · Integrity hooks · admin UI. Security harden: token↔UUID bind · enroll cap/rate-limit/replay · skip-integrity lab gate |
| Zero-touch prod gates | Railway HTTPS up — `https://eldershield.up.railway.app` (`/health` OK). AAB `-Peldershield.baseUrl` + Play Integrity ADC still operator |
| Integrity nonce bind | Code ready (#11) — client sends `integrityNonce`; server checks requestDetails when Integrity enabled |
| `ADMIN_NOTIFY_WEBHOOK_URL` | Optional (unset) |
| Lab device smoke | Pass 2026-11-21 — `scripts/lab-full-verify.ps1` · AVD L4–L8 gsm PASS · S22 nocall banks (Toss/KB/Woori/NH/SOL) + BD coexist · see `2026-11-21-lab-full-verify-results.json` |
| Public GitHub visibility | **PUBLIC** as of 2026-11-20 (authority handoff) |

## Notes

- Fail-open EmptyNoBlock unchanged
- ElderShield must not use Overlay / Accessibility / Device Admin
