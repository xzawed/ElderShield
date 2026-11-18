# ElderShield

<p align="center">
  <strong>Defensive guard for parents’ Android devices</strong><br/>
  Block high-risk country calls &amp; web access · Detect suspicious apps · Admin-only control
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"></a>
  <img alt="Platform" src="https://img.shields.io/badge/Android-minSdk%2029-3DDC84?logo=android&logoColor=white">
  <img alt="Backend" src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white">
  <img alt="Status" src="https://img.shields.io/badge/Status-Phase%201%20planning-orange">
  <img alt="Visibility" src="https://img.shields.io/badge/Repo-Private-lightgrey">
</p>

<p align="center">
  <a href="#eldershield">English</a> · <a href="#eldershield-실버실드">한국어</a>
</p>

---

## What it is

**ElderShield** (실버실드) protects parents’ phones and tablets with a **hands-off** defensive layer:

| Capability | Phase 1 approach |
|------------|------------------|
| Risky-country **calls** | `CallScreeningService` + cached rules |
| Risky-country **internet** | Private DNS (NextDNS / AdGuard); VPN later |
| **Scam / sideloaded apps** | Scan & report to admin only (no parent popups) |
| **Control plane** | Admin web dashboard + versioned rule sync |

Parents install once and grant permissions. **No day-to-day UI.** You manage rules remotely.

> Complements (does not replace) tools like Bitdefender.

---

## Hard constraints

These are non-negotiable product rules:

- **Zero friction for parents** — silent rule updates, minimal notifications  
- **Banking-app safe** — `VpnService` off by default; no Overlay / Accessibility / Device Admin  
- **Defense only** — no counter-attacks, no forced remote wipes  
- **Multi-country lists** — restrictions stay as selectable arrays, not single picks  

Full design: [`docs/specs/2026-11-18-eldershield-system-design.md`](docs/specs/2026-11-18-eldershield-system-design.md)

---

## Architecture (at a glance)

```text
Admin Web  ──HTTPS + API Key──▶  Backend (FastAPI)
                                      │
                         WorkManager pull (rules)
                                      ▼
                              Android app
                    CallScreening · Sync · Scanner · Room
```

**Stack (planned):** FastAPI + SQLModel/Alembic · Kotlin Android (`com.eldershield`) · Admin UI (HTMX or Vue)

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/README.md`](docs/README.md) | Documentation index |
| [`docs/00-product-overview.md`](docs/00-product-overview.md) | Product summary |
| [`docs/01-architecture.md`](docs/01-architecture.md) | Architecture summary |
| [`docs/06-roadmap.md`](docs/06-roadmap.md) | Milestones |
| [`docs/plans/`](docs/plans/) | Schedule, WBS, review gates |
| [`docs/specs/`](docs/specs/) | Design SSOT & unit-test design |
| [`AGENTS.md`](AGENTS.md) | Agent / contributor working rules |

---

## Status

Phase **1** is in **planning / docs**. Implementation order: **Backend → Admin UI → Android**, with TDD on matching & versioning logic first.

Roadmap: [`docs/06-roadmap.md`](docs/06-roadmap.md)

---

## License

Licensed under the **Apache License, Version 2.0**. See [`LICENSE`](LICENSE).

```text
Copyright 2026 xzawed
```

---

## ElderShield (실버실드)

<p>
  <img alt="라이선스" src="https://img.shields.io/badge/라이선스-Apache%202.0-blue.svg">
  <img alt="상태" src="https://img.shields.io/badge/상태-Phase%201%20기획-orange">
</p>

부모님 Android 기기용 **방어적 Guard**입니다. 위험 국가 전화·인터넷을 막고, 출처 불명/사기 앱을 탐지해 **관리자 대시보드로만** 보고합니다. 부모님은 설치·권한 허용 후 추가 조작이 없습니다.

### 핵심 제약

- 부모님 불편 제로 · 무인지 업데이트  
- 은행 앱 호환 (VpnService 기본 비활성, Overlay/Accessibility/Device Admin 금지)  
- 합법적 방어만 · 제한 국가 **다중 선택** 유지  

### 문서

전체 설계·일정·테스트 설계는 [`docs/README.md`](docs/README.md)를 보세요.  
에이전트 작업 규칙: [`AGENTS.md`](AGENTS.md)

### 라이선스

Apache License 2.0 — [`LICENSE`](LICENSE)
