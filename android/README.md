# ElderShield Android

Package: `com.eldershield` · minSdk 29

## Modules

| Module | Role |
|--------|------|
| `:core` | Pure JVM domain (matcher, sync, scorer, DNS) + unit tests |
| `:app` | Room, WorkManager, CallScreening, admin provisioning UI |

## Test (no device)

```bash
cd android
./gradlew :core:test
```

## Debug APK

1. `local.properties` → `sdk.dir=...`
2. `./gradlew :app:assembleDebug`
3. Device steps: [`../docs/runbooks/device-test.md`](../docs/runbooks/device-test.md)

| Build | Cleartext HTTP |
|-------|----------------|
| `debug` | Allowed (LAN lab) |
| `release` | Disabled |

Hard constraints: no VpnService / Overlay / Accessibility / Device Admin.
