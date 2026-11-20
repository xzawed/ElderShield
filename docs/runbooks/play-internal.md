# Play internal testing track (S6.2 · v0.2.0)

Operator-owned Console steps. Engineering preconditions below.

## Preconditions (engineering)

| Item | Requirement |
|------|-------------|
| Version | `versionName` **0.2.0** / `versionCode` **2** (align with `docs/releases/v0.2.0.md`) |
| Bundle | `cd android && ./gradlew :app:bundleRelease` → signed AAB when `keystore.properties` present |
| Signing | Copy `android/keystore.properties.example` → `keystore.properties` (gitignored) + upload `.jks` path |
| Manifest | `usesCleartextTraffic=false`; no Overlay / Accessibility / Device Admin |
| VpnService | Default **off**; no `BIND_VPN_SERVICE` |
| Privacy | Minimize phone-number logging |

### Unsigned lab smoke

Without keystore: `assembleRelease` still builds (unsigned). Play Console requires a **signed** AAB.

```bash
cd android
# optional: copy keystore.properties.example → keystore.properties and fill
./gradlew :app:bundleRelease
# out: app/build/outputs/bundle/release/app-release.aab
```

## Operator checklist (Play Console)

1. Create/select app → **Internal testing** track.  
2. Upload signed AAB; fill Data safety / permissions declarations.  
3. Add internal testers (email list).  
4. Install from Play internal link on S22 / Note 10+ (not sideload debug).  
5. Provision over **HTTPS** backend only.  
6. Re-run [`device-test.md`](device-test.md) §8 where applicable; confirm heartbeat health + DNS.

## Out of scope here

- Production / public track  
- GitHub Public visibility flip (separate operator decision)  
- Store listing localization beyond Phase 1
