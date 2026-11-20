# Admin / device API keys

**Startup:** process refuses `change-me-admin` / `change-me-device` and identical admin/device keys.  
**Local only:** `ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1`.

**Admin UI cookie:** HMAC session (`eldershield_admin_session`), never the raw key.  
Production HTTPS: set `COOKIE_SECURE=1`.

**Android:** provision `device_api_key` (and `base_url`) in SharedPreferences — blank key → WorkManager retry, no insecure default.

## Key rotation (Phase 2A)

1. Generate new distinct `ADMIN_API_KEY` / `DEVICE_API_KEY` (not `change-me-*`).
2. Deploy backend with new env; keep old keys only if you briefly dual-accept (not implemented — prefer short maintenance window).
3. Re-provision Android SharedPreferences `device_api_key` on each device (silent sync resumes after key set).
4. Re-login Admin UI with the new admin key (old session cookie invalid).
5. Optional: rotate `NEXTDNS_API_KEY` / webhook URL in the same window; see [`backup-restore.md`](backup-restore.md).
