# Admin Log Visibility — Implementation Plan

> **For agentic workers:** Subagent-driven or inline execution. Checkbox tasks.

**Goal:** SPA로 Incident·기기·audit·NextDNS 로그를 요약·도표·타임라인으로 제공한다 (범위 C, 순서 L1→L2→L3, 안1).

**Spec:** [`../specs/2026-11-21-admin-log-visibility-design.md`](../specs/2026-11-21-admin-log-visibility-design.md)

**Stack:** React SPA (`admin-web`) · Recharts · FastAPI admin API · NextDNS logs proxy

## Constraints

- 전화번호 원문 금지; hash/last4만
- Cookie + `X-ElderShield-Admin: 1`
- PDF/Grafana 비범위
- 자동 커밋 금지

## Tasks

### L1 Incident detail

- [ ] `spa.py`: SPA shell for `incidents/{id}`, nested `devices/{uuid}`
- [ ] `admin-web`: IncidentPage, timeline merge util + tests, DNS chart
- [ ] ThreatTable → `/incidents/:id`; API `getIncidentExport`
- [ ] pytest SPA static paths

### L2 Device + Audit

- [ ] DeviceDetailPage from `GET /devices/{uuid}`
- [ ] AuditPage from `GET /audit`; nav SPA
- [ ] Devices list row → detail

### L3 NextDNS logs

- [ ] `GET /api/v1/admin/dns-logs` (503 if unset)
- [ ] DnsLogsPage + nav
- [ ] pytest mock httpx

### Verify

- [ ] full pytest + `npm run build` + smoke updates
