# Admin UI (Tailwind)

**Stack:** Jinja2 templates + **Tailwind CSS CDN** (`cdn.tailwindcss.com`) + HTMX  
**Entry:** `/admin/ui/login` → HMAC session cookie (see [`admin-api-keys.md`](admin-api-keys.md))

## Look & layout

| Surface | Design |
|---------|--------|
| Sign-in | Centered card, Fraunces display + Source Sans 3, teal brand |
| Authenticated | Dark ink sidebar + light content, status pill, panel cards |
| Tables | Enterprise-style headers, badges for DNS / enabled / risk |

Brand tokens (Tailwind `theme.extend`): `brand.*` teal, `ink.*` slate/navy — not purple defaults.

## Pages

| Path | Purpose |
|------|---------|
| `/admin/ui/login` | Admin API key → session |
| `/admin/ui/restrictions` | Country restriction groups |
| `/admin/ui/restrictions/new` · `/{id}` | Create / edit (multi-select `countries`). `applyTo=call` → device CallScreening; `dns`/`internet` → admin denylist / NextDNS sync (device does not VPN-filter) |
| `/admin/ui/call-rules` | Call whitelist rules (exact E.164 lines → `callRules`) |
| `/admin/ui/dns-denylist` | NextDNS `security.tlds` + denylist hosts; optional **Sync to NextDNS** (`NEXTDNS_*` env) |
| `/admin/ui/devices` | Heartbeat + protection degraded badge · **enrollment window** open/close |
| `/admin/ui/devices/{uuid}` | Device detail — health events · **revoke device token** · recent scans |
| `/admin/ui/devices/{uuid}/scans` | Scan results (`reasons[]`) |
| `/admin/ui/allowlist` | App allowlist (false-positive packages) |
| `/admin/ui/audit` | Admin mutation audit log |

## Visual verification

With backend running:

```bash
cd backend
# set ADMIN_API_KEY / DEVICE_API_KEY (non change-me-*)
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Then open `/admin/ui/login` in a browser (or Cursor browser / Playwright MCP):

1. Confirm Tailwind styles load (sidebar/card spacing, not unstyled HTML).  
2. Sign in with admin key → restrictions list.  
3. Open **Call rules** → add a full E.164 whitelist line → row appears; `GET /api/v1/rules/latest` includes `callRules`.  
4. Open Devices → enrollment window controls · heartbeat rows + degraded badges; open a device **Detail** for health events / token revoke.  
5. Allowlist / Audit nav entries load (Phase 2A).

Automated regression: `pytest -q tests/test_admin_ui_multiselect.py tests/test_admin_ui_call_rules.py tests/test_phase2_health_and_audit.py`

## Phase note

CDN Tailwind remains intentional. A CLI-built `static/app.css` can replace the CDN later without changing class names.
