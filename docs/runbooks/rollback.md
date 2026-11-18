# Rule rollback (M6)

**API:** `POST /api/v1/admin/rules/rollback` (admin API key)  
**Effect:** restore a prior restriction snapshot as a **new** version (history kept).

## Steps

1. Confirm current `GET /api/v1/rules/latest` `version`.
2. Identify target snapshot version (from admin history / version table).
3. Call rollback with admin key; verify `version` increased and content matches snapshot.
4. Wait for device `RuleSyncWorker` (≤1h) or trigger sync; confirm device `lastRuleVersion`.

## Notes

- Devices fail open if cache empty and sync fails (no call block).
- Do not expose rollback status on the parent phone UI.
