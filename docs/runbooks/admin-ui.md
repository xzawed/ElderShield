# Admin UI

**Stack (현재):** React SPA (`admin-web`) under `/admin/ui/` + **레거시 Jinja 폼** (생성·편집만)  
**Entry:** `/admin/ui/login` → HMAC session cookie (see [`admin-api-keys.md`](admin-api-keys.md))  
**설계:** [`../specs/2026-11-21-admin-react-spa-dashboard-design.md`](../specs/2026-11-21-admin-react-spa-dashboard-design.md)

## Auth

- Cookie `eldershield_admin_session` + SPA API calls send `X-ElderShield-Admin: 1`
- Logout: `/admin/ui/logout` (same Secure/SameSite/Path as login)

## Primary nav (SPA shell — must not swap templates)

| Path | Purpose |
|------|---------|
| `/admin/ui/` | Dashboard KPI · threats · policy |
| `/admin/ui/devices` | Device list |
| `/admin/ui/devices/{uuid}` | Health · scans · incidents · token revoke |
| `/admin/ui/restrictions` | Country restriction **list** (read) |
| `/admin/ui/call-rules` | Call rules **list** (read) |
| `/admin/ui/dns-denylist` | Denylist summary |
| `/admin/ui/dns-logs` | NextDNS query logs (503 UI if unset) |
| `/admin/ui/allowlist` | App allowlist **list** (read) |
| `/admin/ui/audit` | Audit log |
| `/admin/ui/incidents/{id}` | Incident evidence |

## Legacy Jinja forms (until Phase B CRUD)

| Path | Purpose |
|------|---------|
| `/admin/ui/restrictions/new` · `/{id}` | Create / edit multi-select `countries` |
| call-rules / allowlist create·delete forms | Still Jinja POST; sidebar links return to SPA lists |

Jinja `base.html` nav points at SPA list URLs so leaving a form restores the React sidebar.

## Look

Dark ink sidebar + light canvas · Fraunces + Source Sans 3 · brand teal (`brand.*` / `ink.*`).

## Verify

```bash
cd admin-web && npm ci && npm run build
cd ../backend && .venv/Scripts/python.exe -m pytest tests/test_admin_spa_static.py -q
```

```powershell
powershell -File scripts/lab-admin-spa-smoke.ps1
# expects spa-nav-shell-unity PASS
```

Browser: open `/admin/ui/` → click every primary sidebar item → **sidebar chrome must stay SPA** (no Jinja reorder/missing items).
