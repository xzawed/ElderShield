# Play internal testing track (S6.2)

Operator-owned Console steps. Engineering preconditions only below.

## Preconditions (engineering)

| Item | Requirement |
|------|-------------|
| Release APK/AAB | `assembleRelease` / bundle — **not** debug cleartext |
| Manifest | `usesCleartextTraffic=false` on release; no Overlay / Accessibility / Device Admin |
| VpnService | Default **off** (bank-app hard constraint) |
| Signing | Upload key / Play App Signing configured by operator |
| Privacy | Minimize phone-number logging; screening logs must not print raw numbers |

## Operator checklist (Play Console)

1. Create/select app → **Internal testing** track.  
2. Upload signed AAB; fill Data safety / permissions declarations.  
3. Add internal testers (email list).  
4. Install from Play internal link on S22 / Note 10+ (not sideload debug).  
5. Provision over **HTTPS** backend only (no `adb reverse` HTTP in production path).  
6. Re-run device-test.md §8 matrix where applicable (CN via emulator still valid for gsm).

## Out of scope here

- Production rollout / public track  
- Store listing copy localization beyond Phase 1
