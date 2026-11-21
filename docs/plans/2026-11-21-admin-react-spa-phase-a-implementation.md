# Admin React SPA Dashboard — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a premium React admin shell with Dashboard (KPI + threats + policy) and Devices list, served under `/admin/ui`, using existing admin APIs—without regressing remaining Jinja CRUD **forms**.

**Architecture:** Vite React SPA in `admin-web/` builds into `backend/app/static/admin-spa/`. FastAPI serves SPA for `/admin/ui/` and `SPA_SHELL_SEGMENTS` (includes policy **list** paths). Jinja keeps create/edit forms (`/restrictions/new`, etc.) until Phase B CRUD. Auth via session cookie + `X-ElderShield-Admin: 1`.

**Post-A note (S6.7):** Phase A sidebar Jinja `<a href>` links caused fatal shell swap. Superseded — primary nav is React `Link` only; see design §2 셸 통일.

**Tech Stack:** React 18 · Vite · TypeScript · React Router 6 · Tailwind 3 · Recharts · FastAPI StaticFiles · pytest

**Spec:** [`../specs/2026-11-21-admin-react-spa-dashboard-design.md`](../specs/2026-11-21-admin-react-spa-dashboard-design.md)

## Global Constraints

- Phase **A only** (shell, login, dashboard, devices read). No full CRUD migration yet
- Visual: teal/ink + Fraunces/Source Sans 3; no purple glow / Inter default stack
- 부모님 Android · VpnService · 알림 무관
- **자동 커밋 금지** (사용자 요청 시에만)
- 운영 도메인: `https://eldershield.up.railway.app`
- VirtualBox 등 사용자 VM 건드리지 않음; 에뮬 랩 시 종료 후 회수

---

## File map

| Path | Responsibility |
|------|----------------|
| `admin-web/package.json` | Vite React TS deps |
| `admin-web/vite.config.ts` | `base: '/admin/ui/'`, proxy `/api` → `:8765`, outDir → `../backend/app/static/admin-spa` |
| `admin-web/tailwind.config.js` | brand/ink tokens matching Jinja |
| `admin-web/src/main.tsx` | bootstrap |
| `admin-web/src/App.tsx` | Router |
| `admin-web/src/api/client.ts` | fetch wrapper, credentials include, 401→login |
| `admin-web/src/api/admin.ts` | typed admin GETs |
| `admin-web/src/i18n/` | ko/en JSON + hook reading `es_admin_lang` cookie |
| `admin-web/src/layouts/AdminShell.tsx` | dark sidebar + outlet |
| `admin-web/src/pages/LoginPage.tsx` | premium login |
| `admin-web/src/pages/DashboardPage.tsx` | KPI, threats, charts, policy |
| `admin-web/src/pages/DevicesPage.tsx` | list + summary strip |
| `admin-web/src/components/KpiStrip.tsx` | KPI row |
| `admin-web/src/components/StatusBadge.tsx` | normal/degraded/risk |
| `backend/app/web/spa.py` | mount static + SPA fallback for Phase A paths |
| `backend/app/main.py` | include spa routes; fix `/admin/ui` redirect |
| `backend/app/web/auth.py` | post-login redirect → `/admin/ui/` (SPA home) when SPA built |
| `backend/Dockerfile` or Railway build | `npm ci && npm run build` in admin-web |
| `backend/tests/test_admin_spa_static.py` | SPA index served when present |
| `docs/README.md` | index plan |

---

### Task 1: Scaffold `admin-web` Vite + Tailwind tokens

**Files:**
- Create: `admin-web/` (package.json, vite.config.ts, tsconfig, index.html, src/main.tsx, src/index.css)
- Create: `admin-web/tailwind.config.js`, `postcss.config.js`

**Interfaces:**
- Produces: `npm run build` writes to `backend/app/static/admin-spa/`
- Produces: Vite `base: '/admin/ui/'`

- [x] **Step 1: Scaffold**

```bash
cd f:/DEVELOPMENT/SOURCE/GROK/ElderShield
npm create vite@latest admin-web -- --template react-ts
cd admin-web
npm i
npm i -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm i react-router-dom recharts
```

- [x] **Step 2: Configure vite.config.ts**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/admin/ui/',
  build: {
    outDir: path.resolve(__dirname, '../backend/app/static/admin-spa'),
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
      // login cookie endpoints still on Jinja until SPA login posts to same origin
      '/admin/ui/login': 'http://127.0.0.1:8765',
      '/admin/ui/logout': 'http://127.0.0.1:8765',
      '/admin/ui/lang': 'http://127.0.0.1:8765',
    },
  },
})
```

Note: During SPA development, prefer SPA login page posting to a small JSON login endpoint (Task 2) to avoid HTML form conflict. If adding JSON login, document in Task 2.

- [x] **Step 3: Tailwind theme** — copy brand/ink/fontFamily from `backend/app/templates/admin/base.html`

- [x] **Step 4: Verify**

```bash
cd admin-web && npm run build
# expect backend/app/static/admin-spa/index.html
```

- [ ] **Step 5: Commit only if user requested**

---

### Task 2: API client + optional JSON login for SPA

**Files:**
- Create: `admin-web/src/api/client.ts`, `admin-web/src/api/admin.ts`
- Modify: `backend/app/web/admin_ui.py` or `auth.py` — add `POST /admin/ui/api/login` JSON `{apiKey}` → Set-Cookie + `{ok:true}` (keeps cookie auth identical)
- Test: `backend/tests/test_admin_spa_login_json.py`

**Interfaces:**
- Produces: `apiGet<T>(path)`, `apiPost<T>(path, body)`
- Produces: `POST /admin/ui/api/login` → 200 + session cookie; 401 on bad key
- Existing form `POST /admin/ui/login` remains for Jinja

- [x] **Step 1: Failing pytest for JSON login**

```python
def test_json_login_sets_session(client):
    r = client.post("/admin/ui/api/login", json={"apiKey": "test-admin-key"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "session" in r.cookies or any("elder" in c.lower() or "session" in c.lower() or "admin" in c.lower() for c in r.cookies)
```

Inspect `backend/app/web/auth.py` for actual cookie name and reuse `set_admin_session`.

- [x] **Step 2: Implement JSON login + client.ts**

```ts
export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(path, { credentials: 'include' })
  if (r.status === 401) {
    window.location.assign('/admin/ui/login')
    throw new Error('unauthorized')
  }
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
```

Admin paths: `/api/v1/admin/devices`, etc., with header if cookie alone insufficient — check how Jinja admin authenticates API calls (cookie vs key). If admin UI only gates HTML and API needs `X-API-Key`, store key in session server-side and add `GET /admin/ui/api/me` that proxies, **or** have JSON login also return short-lived pattern matching existing tests.

**Critical:** Read `require_admin` / TestClient ADMIN header pattern. Prefer: session cookie unlocks HTML; for `/api/v1/admin/*` browser calls, either (a) inject API key from server-side BFF or (b) extend `require_admin` to accept valid admin session cookie. **Phase A recommended: (b)** — `require_admin` OR session cookie valid → allow. Implement in `backend/app/api/deps.py` + test.

- [x] **Step 3: pytest PASS for login + one admin GET with cookie only**

- [ ] **Step 4: Commit only if user requested**

---

### Task 3: AdminShell + LoginPage + Router

**Files:**
- Create: `admin-web/src/layouts/AdminShell.tsx`
- Create: `admin-web/src/pages/LoginPage.tsx`
- Create: `admin-web/src/App.tsx`
- Create: `admin-web/src/i18n/ko.json`, `en.json`, `useI18n.ts`

**Interfaces:**
- Sidebar links: Dashboard `/admin/ui/`, Devices `/admin/ui/devices`, then **external** Jinja links for restrictions/call-rules/dns/allowlist/audit (full URL paths under `/admin/ui/...` same host — SPA router must not catch them if served by Jinja; see Task 6)
- Login posts to `/admin/ui/api/login`, then `navigate('/')`

- [x] **Step 1: Implement shell** — dark ink-950 sidebar, Fraunces brand, active teal highlight, lang toggle hitting `/admin/ui/lang?set=`

- [x] **Step 2: Login page** — premium form (no purple); API key field; error state

- [x] **Step 3: Router**

```tsx
<BrowserRouter basename="/admin/ui">
  <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route element={<AdminShell />}>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/devices" element={<DevicesPage />} />
    </Route>
  </Routes>
</BrowserRouter>
```

- [x] **Step 4: Visual check** `npm run dev` — login + empty dashboard shell

---

### Task 4: DashboardPage (KPI + threats + policy + charts)

**Files:**
- Create: `admin-web/src/pages/DashboardPage.tsx`
- Create: `admin-web/src/components/KpiStrip.tsx`, `StatusBadge.tsx`, `ThreatTable.tsx`, `PolicyCards.tsx`, `HealthCharts.tsx`
- Optional: `GET /api/v1/admin/dashboard/summary` if client fan-out is too heavy — prefer client aggregate first from:
  - `GET /api/v1/admin/devices`
  - For each device or batch: incidents via `GET .../devices/{uuid}/incidents` (limit recent globally by sorting client-side; if too slow add summary endpoint in same task)
  - `GET /api/v1/admin/country-restrictions`
  - `GET /api/v1/admin/dns-denylist`
  - `GET /health` or rules latest admin
  - enrollment window admin endpoint (find in admin.py)

**Interfaces:**
- KPI: `devices`, `degraded`, `dnsOff`, `screeningOff`
- Threats: last N incidents across devices (uuid, triggers, triggeredAt); top scans if available from device detail scans
- Policy: unique country count, tld count, bundleVersion, enroll enabled

- [x] **Step 1: Wire data loaders with loading/error skeletons (styled, not empty gray box only)**

- [x] **Step 2: Recharts donut (ok vs degraded) + simple bar if incident timestamps exist; else omit bar gracefully**

- [x] **Step 3: Motion: CSS fade-in on KPI strip (2–3 intentional motions max)**

- [x] **Step 4: Manual verify against local backend with seeded devices**

---

### Task 5: DevicesPage + summary strip

**Files:**
- Create: `admin-web/src/pages/DevicesPage.tsx`

**Interfaces:**
- Table columns: uuid (short), appVersion, dnsConfigured, callScreeningEnabled, protectionDegraded, lastSyncAt, lastRuleVersion
- Summary strip: counts matching KPI subset
- Row click → for Phase A link to Jinja ` /admin/ui/devices/{uuid} ` (full page) OR SPA placeholder route that redirects

- [x] **Step 1: Implement table + strip**
- [x] **Step 2: Verify with TestClient-seeded data / manual**

---

### Task 6: FastAPI SPA static serving + coexistence with Jinja

**Files:**
- Create: `backend/app/web/spa.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/web/auth.py` — after login redirect to `/admin/ui/` (trailing path that loads SPA)
- Test: `backend/tests/test_admin_spa_static.py`

**Interfaces:**
- If `static/admin-spa/index.html` exists:
  - `GET /admin/ui/` and `GET /admin/ui/devices` and `GET /admin/ui/login` serve SPA index **OR** keep Jinja login until SPA login works — Phase A: SPA owns `/admin/ui/`, `/admin/ui/login`, `/admin/ui/devices` (exact + assets under `/admin/ui/assets/*`)
  - Jinja keeps `/admin/ui/restrictions`, `call-rules`, `dns-denylist`, `allowlist`, `audit`, `devices/{uuid}` detail
- Mount StaticFiles for assets at `/admin/ui/assets`

Implementation sketch:

```python
SPA_DIR = Path(__file__).resolve().parents[1] / "static" / "admin-spa"
SPA_PATHS = {"", "login", "devices"}  # first segment after /admin/ui/

@router.get("/{full_path:path}")
async def spa_or_404(full_path: str):
    # only if not claimed by more specific Jinja routes registered first
    ...
```

**Order matters:** Register Jinja `admin_ui.router` **before** SPA catch-all; SPA catch-all only for allowlisted first segments.

- [x] **Step 1: pytest** — with tmp index.html in spa dir, `GET /admin/ui/` returns 200 html containing root div; `GET /admin/ui/restrictions` still Jinja 200

- [x] **Step 2: Implement**
- [x] **Step 3: Change root redirect `/` and post-login to `/admin/ui/`**

---

### Task 7: Docker/Railway build hook + docs

**Files:**
- Modify: `backend/Dockerfile` and/or root build — install node, `cd admin-web && npm ci && npm run build`
- Modify: `.github/workflows/*` if CI images backend without frontend — add admin-web build step before pytest or as artifact
- Modify: `docs/runbooks/railway-backend.md` — note SPA build
- Modify: `docs/specs/2026-11-21-admin-react-spa-dashboard-design.md` status → Approved + Phase A plan
- Modify: `docs/README.md` — index this plan
- Modify: `docs/plans/2026-11-19-sprint-board.md` Status one line

- [x] **Step 1: Dockerfile multi-stage or apt node**
- [x] **Step 2: Document local `npm run build` before uvicorn**
- [ ] **Step 3: Commit only if user requested**

---

### Task 8: Phase A acceptance smoke

**Files:**
- Create: `scripts/lab-admin-spa-smoke.ps1` — curl login JSON, curl `/admin/ui/`, curl `/api/v1/admin/devices` with cookie jar against `ELDERSHIELD_LAB_URL` default `https://eldershield.up.railway.app`

- [x] **Step 1: Local smoke PASS**
- [x] **Step 2: After deploy, production smoke PASS**

---

## Spec coverage (Phase A)

| Spec item | Task |
|-----------|------|
| React+Vite+Tailwind+Recharts | T1, T4 |
| KPI + threats + policy home | T4 |
| Devices list + summary | T5 |
| Cookie auth / API | T2 |
| SPA under `/admin/ui` | T6 |
| Jinja coexistence | T6 |
| Railway build | T7 |
| Premium visual constraints | T3–T5 |
| Phase B/C | out of this plan |

---

## Execution handoff

Plan saved to `docs/plans/2026-11-21-admin-react-spa-phase-a-implementation.md`.

**실행 방식:**

1. **Subagent-Driven (권장)** — 태스크마다 서브에이전트 + 리뷰  
2. **Inline Execution** — 이 세션에서 연속 구현  

어느 쪽으로 진행할까요?
