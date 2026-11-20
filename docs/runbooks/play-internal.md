# Play internal testing track (S6.2 · v0.2.0)

Operator-owned Console steps. Engineering preconditions below.

**계정 인증 대기 중**이면 앱 생성이 막힙니다 → 그동안 [`play-console-while-waiting.md`](play-console-while-waiting.md) · [`../legal/privacy-policy.md`](../legal/privacy-policy.md).

## Preconditions (engineering)

| Item | Requirement |
|------|-------------|
| Version | `versionName` **0.2.0** / `versionCode` **2** (align with `docs/releases/v0.2.0.md`) |
| Bundle | `cd android && ./gradlew :app:bundleRelease` → signed AAB when `keystore.properties` present |
| Signing | Copy `android/keystore.properties.example` → `keystore.properties` (gitignored) + upload `.jks` path |
| Manifest | `usesCleartextTraffic=false`; no Overlay / Accessibility / Device Admin |
| VpnService | Default **off**; no `BIND_VPN_SERVICE` |
| Privacy | Minimize phone-number logging |

### Signed AAB (local)

With gitignored `android/keystore.properties` + `upload-keystore.jks`:

```bash
cd android
# Required for zero-touch enroll (HTTPS origin only — no device key in binary):
#   eldershield.baseUrl=https://your-backend.example.com
#   eldershield.playCloudProjectNumber=<Google Cloud project number>
# Set via -P… flags or android/local.properties (see local.properties.example).
./gradlew :app:bundleRelease -Peldershield.baseUrl=https://your-backend.example.com
# out: app/build/outputs/bundle/release/app-release.aab
```

Without keystore, `assembleRelease` still builds unsigned APK; Play requires the **signed** AAB above.

### Play Integrity (production enroll)

| Side | Requirement |
|------|-------------|
| Backend | `PLAY_INTEGRITY_ENABLED=1`, `PLAY_PACKAGE_NAME=com.eldershield`, ADC (`GOOGLE_APPLICATION_CREDENTIALS`), `pip install -r requirements-integrity.txt` |
| Android | `eldershield.playCloudProjectNumber` at build time |
| Lab | `ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1` (never production) |

## Operator checklist (Play Console)

1. Create/select app → **Internal testing** track.  
2. Upload signed AAB; fill Data safety / permissions declarations.  
3. Add internal testers (email list).  
4. **Before parent install:** Admin UI → Devices → **Open enrollment window** (default 30 min). Spec: [`../specs/2026-11-20-zero-touch-enroll-design.md`](../specs/2026-11-20-zero-touch-enroll-design.md).  
5. Install from Play internal link on S22 / Note 10+ (not sideload debug). Parent types **no** URL/key — release embeds `BASE_URL` only (`-Peldershield.baseUrl=https://…` at bundle time).  
6. Backend: production enroll needs Play Integrity (`PLAY_INTEGRITY_ENABLED=1` + Google creds). Lab may use `ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1`.  
7. Re-run [`device-test.md`](device-test.md) §8 where applicable; confirm heartbeat health + DNS.

## Out of scope here

- Production / public track  
- GitHub Public visibility flip (separate operator decision)  
- Store listing localization beyond Phase 1
