# Admin / device API keys

**Startup:** process refuses `change-me-admin` / `change-me-device` and identical admin/device keys.  
**Local only:** `ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1`.

**Admin UI cookie:** HMAC session (`eldershield_admin_session`), never the raw key.  
Production HTTPS: set `COOKIE_SECURE=1`.

**Android:** provision `device_api_key` (and `base_url`) in SharedPreferences — blank key → WorkManager retry, no insecure default.
