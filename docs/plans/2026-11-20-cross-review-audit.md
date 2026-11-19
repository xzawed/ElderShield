# Cross-review audit (3+ passes) — 2026-11-20

| Pass | Agent / method | Focus |
|------|----------------|--------|
| 1 | Orchestrator static grep | Toast/Notification/PII/`runBlocking`/secrets |
| 2 | [Security Review](8bff49c1-a497-4e21-974f-987ea7fc3b75) | API keys, fail-open, session, logs |
| 3 | [Bugbot](d8b77f68-ed34-4e0d-a356-faac6559ad11) | Cache race, WorkManager, inefficiency |

## Fixed in this PR

- `ActiveRuleBundleCache.publishIfNewer` — stale Room must not overwrite newer sync
- Unique WorkManager enqueue from MainActivity Save
- Room → memory warm on `ElderShieldApp` start
- Shared `RuleBundleJson` decode/encode (drift reduction)
- Admin UI login `hmac.compare_digest`
- Remove duplicate `import app.models` in `db.py`
- `.gitignore` `*.log` (block accidental uvicorn log commit)

## Accepted / deferred (policy or Phase 2)

- Fail-open on empty cache / exception — SSOT intentional; admin visibility field later
- LAUNCHER provisioning UI — installer surface; parent hide launcher icon later
- `remote.version < cached` keep local — document; force-sync flag later
- scan-result unbounded INSERT — Phase 2 upsert
- PackageAppScanner full rescan each report — battery budget OK for 6h

## Tests

- `pytest -q`
- `./gradlew :core:test :app:assembleDebug`
