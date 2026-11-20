# Backup & restore (Phase 2A)

## SQLite (default local / small deploy)

1. Stop the API process (or ensure no writes).
2. Copy the DB file from `DATABASE_URL` (default `./eldershield.db` under `backend/`).
3. Also copy `.env` offline (never commit): `ADMIN_API_KEY`, `DEVICE_API_KEY`, `NEXTDNS_*`, `ADMIN_NOTIFY_WEBHOOK_URL`.
4. Restore: stop API → replace DB file → start API → `GET /health` should return `status=ok`.

## NextDNS profile

1. Prefer a **dedicated** ElderShield profile (`NEXTDNS_PROFILE_ID`).
2. After DB restore, re-push policy: Admin UI **DNS denylist → Sync NextDNS** or `POST /api/v1/admin/dns-denylist/sync-nextdns`.
3. Confirm Android Private DNS hostname still matches the profile.

## Verification

- Admin UI devices list loads.
- `GET /api/v1/rules/latest` with device key returns a bundle.
- Optional: compare `bundleVersion` on `/health` before/after restore.
