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
| `/admin/ui/restrictions/new` · `/{id}` | Create / edit (multi-select `countries`) |
| `/admin/ui/devices` | Heartbeat status |
| `/admin/ui/devices/{uuid}/scans` | Scan results |

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
3. Open Devices → empty or heartbeat rows with badges.

Automated regression for multi-select: `pytest -q tests/test_admin_ui_multiselect.py`

## Phase note

CDN Tailwind is intentional for Phase 1 speed. A CLI-built `static/app.css` can replace the CDN later without changing class names.
