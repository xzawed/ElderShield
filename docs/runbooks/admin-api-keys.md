# Admin / device API keys

**Startup:** process refuses `change-me-admin` / `change-me-device` and identical admin/device keys.  
**Local only:** `ELDERSHIELD_ALLOW_INSECURE_DEFAULTS=1`.

**Admin UI cookie:** HMAC session (`eldershield_admin_session`), never the raw key.  
Production HTTPS: set `COOKIE_SECURE=1`.  
Cookie-authenticated `/api/v1/admin/*` also requires header `X-ElderShield-Admin: 1` (SPA sends it; blocks top-level CSRF GET). Logout clears the cookie with the same `Secure`/`SameSite`/`Path` flags used at login.

**Android (debug/lab):** provision shared `device_api_key` + `base_url` (or **Lab: enroll** / `scripts/lab-enroll-device.ps1`). Blank key → WorkManager retry, no insecure default.

**Android (Play release):** APK에는 장기 device key 없음. `BASE_URL`만 빌드 주입 → `POST /devices/enroll` → **기기별 토큰**을 EncryptedSharedPreferences에 저장. `X-API-Key`에 그 토큰을 넣음.  
서버는 공유 `DEVICE_API_KEY`(랩) **또는** 해시된 기기 토큰을 수용. 스펙: [`../specs/2026-11-20-zero-touch-enroll-design.md`](../specs/2026-11-20-zero-touch-enroll-design.md).

**Enroll lab:** `ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1`. Production: `PLAY_INTEGRITY_ENABLED=1` + ADC + `requirements-integrity.txt`.

## Key rotation (Phase 2A)

1. Generate new distinct `ADMIN_API_KEY` / `DEVICE_API_KEY` (not `change-me-*`).
2. Deploy backend with new env; keep old keys only if you briefly dual-accept (not implemented — prefer short maintenance window).
3. **Lab devices:** re-provision SharedPreferences shared key, **or** open enrollment window and re-enroll.  
   **Release devices:** Admin → device detail → **Revoke device token**, open enrollment window, parent reopens app (or reinstall) to re-enroll.
4. Re-login Admin UI with the new admin key (old session cookie invalid).
5. Optional: rotate `NEXTDNS_API_KEY` / webhook URL in the same window; see [`backup-restore.md`](backup-restore.md).
