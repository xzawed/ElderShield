# ElderShield Android

Package: `com.eldershield` · minSdk 29

## Modules

| Module | Role |
|--------|------|
| `:core` | Pure JVM domain (RuleBundle, RuleSyncPolicy) + UT-A-30..33 |
| `:app` | Room cache, RuleSyncWorker, minimal MainActivity |

## Test (no Android SDK required)

Requires JDK 17+ (21 recommended). Set `JAVA_HOME` then:

```bash
cd android
./gradlew :core:test
```

UT-A-30..33 live in `:core` (`RuleSyncPolicyTest`).

## App build (requires Android SDK)

1. Copy `local.properties.example` → `local.properties` and set `sdk.dir`
2. Ensure `include(":app")` in `settings.gradle.kts`
3. `./gradlew :app:assembleDebug`

VpnService / Overlay / Accessibility / Device Admin are **not** used.
