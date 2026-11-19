# Play internal testing track (S6.2)

Operator-owned Console steps. Engineering preconditions only below.

## Preconditions (engineering)

| Item | Requirement |
|------|-------------|
| Release APK/AAB | `./gradlew :app:assembleRelease` → `app-release-unsigned.apk` (lab smoke 2026-11-19); Play needs **signed AAB** |
| Manifest | `usesCleartextTraffic=false` (verified in `app` manifest); no Overlay / Accessibility / Device Admin |
| VpnService | Default **off** (bank-app hard constraint); no `BIND_VPN_SERVICE` |
| Signing | Upload keystore + Play App Signing — **operator** (not in repo) |
| Privacy | Minimize phone-number logging; screening logs must not print raw numbers |
| Version | `versionName` 0.1.0 / `versionCode` 1 (align with `docs/releases/v0.1.0.md`) |

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
