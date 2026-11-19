# NextDNS setup (S6.3 · country DNS/internet)

SSOT §6.2 — Private DNS path (no VpnService). **Do not** disable Bitdefender (§1.2.1).

## 1. Dedicated profile

1. Create a **new** NextDNS profile used only for ElderShield (do not reuse a personal profile).
2. Note profile id (hostname will be `{id}.dns.nextdns.io`).

## 2. Backend env

In `backend/.env` (never commit secrets):

```env
NEXTDNS_API_KEY=<api-key>
NEXTDNS_PROFILE_ID=<profile-id>
```

Restart uvicorn after change.

## 3. Sync policy

- Admin UI: DNS denylist → **Sync to NextDNS**, or  
- `POST /api/v1/admin/dns-denylist/sync-nextdns` with admin `X-API-Key`

Expect **200** with tlds/domains applied. Without env → **503** (lab OK).

Sync pushes `security.tlds` (e.g. `cn`) + denylist hosts from enabled `applyTo: dns|internet` restrictions.

## 4. Parent phone Private DNS

1. Settings → Network → Private DNS → **Hostname**  
2. Value: `{NEXTDNS_PROFILE_ID}.dns.nextdns.io`  
3. Save. ElderShield heartbeat should eventually show `dnsConfigured=true` when the monitor trusts that host.

## 5. Verify

| Check | Expect |
|-------|--------|
| `GET /api/v1/admin/dns-denylist` | `tlds` / `domains` match policy |
| sync-nextdns | 200 |
| Admin devices | `dnsConfigured=true` after report worker |
| Browser on device | Restricted ccTLD/host fails resolve (NextDNS), bank apps still work (no VPN) |
