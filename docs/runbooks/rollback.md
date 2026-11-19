# Rule rollback (M6)

**API:** `POST /api/v1/admin/rules/rollback` (admin `X-API-Key`)  
**Effect:** restore a prior restriction snapshot as a **new** row version; **RuleBundle generation** always increases (history kept).

## Request

```http
POST /api/v1/admin/rules/rollback
X-API-Key: <admin-key>
Content-Type: application/json

{"restrictionId": "<uuid>", "targetVersion": 1}
```

**Response (200):** restriction fields + `bundleVersion` (device sync key).

## Steps

1. Confirm current `GET /api/v1/rules/latest` `version` (bundle generation).
2. Identify target snapshot: row `version` in `CountryRestrictionVersion` (or admin history).
3. Call rollback with admin key; verify response `bundleVersion` > previous latest and `countries` match snapshot.
4. Wait for device `RuleSyncWorker` (≤1h) or trigger sync; confirm device `lastRuleVersion` equals new `bundleVersion`.

## Notes

- Devices fail open if cache empty and sync fails (no call block).
- Do not expose rollback status on the parent phone UI.
- Device key → 403. Missing snapshot / restriction → 404.

## Lab cleanup (temporary KR call rule)

After 010 national-format smoke on a KR handset:

1. Admin → Country restrictions → disable or delete the **Lab KR call-only** row (keep CN `call`+`dns` if still needed).  
2. Confirm `GET /api/v1/rules/latest` `version` increased and KR is absent or `enabled=false`.  
3. Trigger device Save & sync (or wait for RuleSyncWorker); `lastRuleVersion` matches.  
4. Do **not** tell anyone to disable Bitdefender (§1.2.1).
