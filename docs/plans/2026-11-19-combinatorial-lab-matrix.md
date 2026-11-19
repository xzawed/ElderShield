# Combinatorial lab matrix (call × DNS/internet × app)

Not single-smoke. Axes are orthogonal; each **cell** below is a required case.  
Automation: `scripts/lab-combinatorial-matrix.ps1`.  
Latest run: `docs/plans/2026-11-19-combinatorial-lab-results.json` (PASS=33, SKIP=1 `NEXTDNS_*`).  
**Safety:** `gsm call` / `ACTION.CALL` hard-gated to `emulator-*` only. Physical S22 never auto-dials (see `device-test.md` §8).

## Axes

| Axis | Levels |
|------|--------|
| A `applyTo` | `call` / `dns` / `internet` / `call+dns` / `call+internet` / `dns+internet` / `call+dns+internet` / `disabled` |
| B Call event | `in_CN` / `in_CN_WL` / `in_US` / `in_KR82` / `in_KR010` / `out_CN` / `out_KR` |
| C Own line (`phonenumber`) | `own_KR` / `own_CN` |
| D Private DNS | `off` / `opportunistic` / `hostname_trusted` |
| E App | `bank_toss` / `scanner_unit` / `scan_api_roundtrip` |
| F Role | `held_es` (AVD) / `peers_reported` (S22, no steal) |

## Call expected (when restriction country = CN or KR as noted)

| applyTo contains `call`? | Event | Expect |
|--------------------------|-------|--------|
| yes + CN | `in_CN` | Reject |
| yes + CN | `in_CN_WL` | Allow |
| yes + CN | `in_US` / `out_CN` / `out_KR` | Allow |
| yes + KR | `in_KR82` / `in_KR010` | Reject |
| **no** (dns/internet/disabled only) | `in_CN` | **Allow** |
| any | own line CN/KR | does not alone change expect |

## DNS / internet expected

| applyTo | `GET dns-denylist` | `dnsConfigured` when hostname trusted |
|---------|-------------------|----------------------------------------|
| includes `dns` or `internet` | CN → tlds/domains non-empty | true if Private DNS trusted |
| call-only / disabled | no CN from that row | reporting still works |

## App expected

| Case | Expect |
|------|--------|
| Toss launch | starts; no ES overlay/VPN |
| `:core` AppRiskScorer tests | green |
| scan-result POST + admin GET | 200; row visible if score threshold met |

## Coverage policy

- Full product of A×B is required for **call correctness** (applyTo isolation).  
- C×B sampled (own_CN × in_CN, own_CN × out_KR).  
- D×A sampled (hostname × dns applyTo → dnsConfigured).  
- E always run once per batch.  
- F: AVD held_es; S22 peers without steal.
