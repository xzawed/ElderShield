# Public-repo readiness — 5-pass verification (2026-11-20)

Repo was **PRIVATE** at check time. Goal: decide if visibility may become **Public**.

## Pass matrix

| Pass | Scope | Result |
|------|--------|--------|
| 1 | Tracked secret filenames / key patterns | **PASS** — no `.env`/pem tracked; placeholders only (`change-me-*`, `test-*-key`, `.env.example`) |
| 2 | docs/plans lab JSON + runbooks | **FAIL→FIXED** — real S22 serial + device UUIDs in lab JSON/scripts (redacted in HEAD) |
| 3 | Git history + gitignore | **WARN** — `.env` never committed; **lab device serial/UUID still in old commits** (pre-redaction) |
| 4 | Android/Backend hardcoding | **PASS** — no live NextDNS/admin keys; `DEFAULT_BASE_URL=https://example.invalid`; release cleartext off |
| 5 | GitHub + local secrets | **PASS/WARN** — remote PRIVATE; local `.env` present & ignored; public switch blocked until history purge |

## Verdict

| Question | Answer |
|----------|--------|
| HEAD (current tree) safe enough? | **Yes**, after serial/UUID redaction in this change |
| Safe to flip Public **right now**? | **No** — Git history still contains lab device serial / UUIDs |
| After history rewrite + force-push? | **Yes**, with operator key rotation if those keys were ever pasted into tickets/chat |

## Required before Public

1. Merge HEAD redaction (scripts use `ELDERSHIELD_S22_SERIAL`).  
2. Rewrite history to remove lab device serial/UUID strings (e.g. `git filter-repo --replace-text`).  
3. Force-push `main` (destructive — coordinate).  
4. Optional: enable GitHub Secret Scanning / push protection.  
5. Keep NextDNS / admin / device keys only in local `.env` or secret store.

## Acceptable in a public OSS tree

- Fake E.164 samples (`+8613812345678`, `01098765432`) in unit tests  
- `test-admin-key` / `test-device-key` in pytest  
- Apache-2.0 LICENSE / SECURITY.md reporting process  
