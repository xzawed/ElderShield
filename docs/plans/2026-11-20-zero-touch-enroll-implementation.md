# Zero-touch Enroll Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parents install from Play with zero URL/key input; release apps enroll via Play Integrity + admin enrollment window and receive per-device API tokens (no long-lived key in the APK).

**Architecture:** Backend issues hashed per-device tokens after Integrity verification while an admin-opened enrollment window is active. `require_device` accepts either the legacy shared `DEVICE_API_KEY` (debug/lab) or a non-revoked device token. Android release embeds only `BASE_URL`, stores the token in EncryptedSharedPreferences, and hides the provision form from parents.

**Tech Stack:** FastAPI · SQLModel · pytest · Android Kotlin · Play Integrity API · EncryptedSharedPreferences · WorkManager

**Spec:** [`../specs/2026-11-20-zero-touch-enroll-design.md`](../specs/2026-11-20-zero-touch-enroll-design.md)

## Global Constraints

- 부모님 불편 제로 · 무인지 규칙 · 알림 최소화 (SSOT)
- Overlay / Accessibility / Device Admin **ElderShield 사용 금지**
- VpnService 기본 비활성 · CallScreening 강탈 금지 (§1.2.1)
- `countries`는 항상 배열
- Release APK에 장기 `DEVICE_API_KEY` **금지**
- Backend → Android 순 · TDD · 자동 커밋 금지(사용자가 요청할 때만)
- Integrity verdict 임계값: **`MEETS_DEVICE_INTEGRITY`** (실측 후 조정 가능)
- Lab/pytest: `ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1` 로 검증기 스킵 허용 (production 기본 OFF)

---

## File map

| Path | Responsibility |
|------|----------------|
| `backend/app/models/device.py` | `Device.api_token_hash`, `token_revoked_at`; `EnrollmentWindow` |
| `backend/app/services/device_tokens.py` | generate/hash/verify device tokens |
| `backend/app/services/integrity.py` | IntegrityVerifier protocol + skip + Google stub |
| `backend/app/api/deps.py` | `require_device` accepts shared key **or** device token |
| `backend/app/api/enroll.py` | `POST /devices/enroll` (no device auth) |
| `backend/app/api/admin.py` | enrollment-window GET/POST · token DELETE |
| `backend/app/web/admin_ui.py` | 등록 창 토글 UI |
| `backend/tests/test_enroll_and_device_tokens.py` | TDD for enroll/window/auth/revoke |
| `android/.../ProvisionStore.kt` | Encrypted prefs: base_url, device_token, device_uuid |
| `android/.../EnrollClient.kt` | POST enroll |
| `android/.../Autoprovision.kt` | release first-run enroll + enqueue workers |
| `android/.../MainActivity.kt` | debug form vs release parent/admin-hidden |
| `android/app/build.gradle.kts` | `buildConfigField BASE_URL` · Integrity dep |
| `docs/runbooks/play-internal.md` · `device-test.md` | 등록 창 ON 한 줄 |

---

### Task 1: Device token helpers + schema fields

**Files:**
- Create: `backend/app/services/device_tokens.py`
- Modify: `backend/app/models/device.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_device_tokens_unit.py`

**Interfaces:**
- Produces: `generate_device_token() -> str`, `hash_device_token(token: str) -> str`, `tokens_match(token: str, token_hash: str) -> bool`
- Produces model fields: `Device.api_token_hash: Optional[str]`, `Device.token_revoked_at: Optional[datetime]`, `EnrollmentWindow` singleton

- [x] **Step 1: Write the failing test** (landed)
- [x] **Step 2–4: Implement + pytest PASS** (`test_device_tokens_unit.py`)

```python
# backend/tests/test_device_tokens_unit.py
from app.services.device_tokens import generate_device_token, hash_device_token, tokens_match

def test_generate_token_is_urlsafe_and_long():
    t = generate_device_token()
    assert len(t) >= 32
    assert t != generate_device_token()

def test_hash_roundtrip():
    t = generate_device_token()
    h = hash_device_token(t)
    assert tokens_match(t, h)
    assert not tokens_match("wrong", h)
```

- [x] **Step 3: Implement helpers + model fields**

```python
# device_tokens.py
import hashlib
import hmac
import secrets

def generate_device_token() -> str:
    return secrets.token_urlsafe(32)

def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def tokens_match(token: str, token_hash: str) -> bool:
    return hmac.compare_digest(hash_device_token(token), token_hash)
```

Add on `Device`:
```python
api_token_hash: Optional[str] = Field(default=None, max_length=64, index=True)
token_revoked_at: Optional[datetime] = None
```

Add:
```python
class EnrollmentWindow(SQLModel, table=True):
    __tablename__ = "enrollment_window"
    id: str = Field(default="default", primary_key=True, max_length=32)
    enabled: bool = False
    expires_at: Optional[datetime] = None
```

Export from `models/__init__.py`.

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit only if user requests** (skip auto-commit)

---

### Task 2: Integrity verifier + enrollment window service

**Files:**
- Create: `backend/app/services/integrity.py`
- Create: `backend/app/services/enrollment_window.py`
- Modify: `backend/app/core/config.py` — `enroll_skip_integrity: bool` from `ELDERSHIELD_ENROLL_SKIP_INTEGRITY`
- Test: `backend/tests/test_enrollment_window_unit.py`

**Interfaces:**
- Produces: `verify_integrity_token(token: str | None) -> bool`
- Produces: `is_enrollment_open(session) -> bool`, `open_enrollment(session, minutes=30)`, `close_enrollment(session)`, `get_enrollment_window(session) -> EnrollmentWindow`

- [ ] **Step 1: Failing tests**

```python
def test_skip_integrity_allows_empty_when_configured(monkeypatch):
    monkeypatch.setenv("ELDERSHIELD_ENROLL_SKIP_INTEGRITY", "1")
    # reload settings or call with skip flag
    assert verify_integrity_token(None) is True

def test_enrollment_closed_by_default(session):
    assert is_enrollment_open(session) is False

def test_open_enrollment_expires(session):
    open_enrollment(session, minutes=30)
    assert is_enrollment_open(session) is True
```

- [ ] **Step 2: Implement**

`verify_integrity_token`: if `settings.enroll_skip_integrity` → True; elif not token → False; else call Google decode stub that for now requires non-empty token and documents TODO wiring of Play Developer API (tests always use skip). Production without skip: reject until Google client wired OR accept only when `GOOGLE_PLAY_INTEGRITY_ENABLED=1` and package matches — for v1 implement:

```python
def verify_integrity_token(integrity_token: str | None) -> bool:
    if settings.enroll_skip_integrity:
        return True
    if not integrity_token:
        return False
    # v1: require non-empty; wire Play Integrity decode in Task 2b when credentials present
    return _google_play_integrity_ok(integrity_token)
```

`_google_play_integrity_ok`: if no Google creds configured → return False (fail closed). If creds present → decode and require `deviceIntegrity.deviceRecognitionVerdict` contains `MEETS_DEVICE_INTEGRITY`.

Enrollment helpers mutate singleton `EnrollmentWindow(id="default")`.

- [ ] **Step 3: pytest PASS**

---

### Task 3: `require_device` accepts device tokens

**Files:**
- Modify: `backend/app/api/deps.py`
- Test: `backend/tests/test_device_token_auth.py`

**Interfaces:**
- Consumes: `hash_device_token`, `Device.api_token_hash`, `token_revoked_at`
- Produces: `require_device` with `Session` dependency

- [ ] **Step 1: Failing test** — heartbeat with per-device token succeeds; revoked fails; wrong fails; shared `test-device-key` still works

- [ ] **Step 2: Change deps**

```python
def require_device(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: Session = Depends(get_session),
) -> None:
    if not x_api_key:
        raise HTTPException(401, detail="Missing API key")
    if x_api_key == settings.device_api_key:
        return
    th = hash_device_token(x_api_key)
    device = session.exec(select(Device).where(Device.api_token_hash == th)).first()
    if device is None or device.token_revoked_at is not None:
        raise HTTPException(403, detail="Device key required")
```

- [ ] **Step 3: pytest full device suite still green**

Run: `pytest tests/test_ut_b_device_api.py tests/test_device_token_auth.py -q`

---

### Task 4: `POST /devices/enroll` + admin window + revoke

**Files:**
- Create: `backend/app/api/enroll.py`
- Modify: `backend/app/main.py` — include router
- Modify: `backend/app/api/admin.py` — window + DELETE token
- Modify: `backend/app/api/schemas.py` — EnrollmentWindowOut
- Modify: `backend/app/web/admin_ui.py` — simple form
- Test: `backend/tests/test_enroll_and_device_tokens.py`

**Request/response:**

```json
// POST /api/v1/devices/enroll
{ "integrityToken": "...", "appVersion": "0.2.0", "model": "SM-S908N" }
// 201
{ "deviceUuid": "...", "deviceToken": "..." }
// 403 enrollment_closed | integrity_failed
```

- [ ] **Step 1: Tests**

| Case | Expect |
|------|--------|
| window closed | 403 `enrollment_closed` |
| window open + skip integrity | 201 + token; hash stored |
| heartbeat with returned token | 200 |
| admin DELETE token | subsequent heartbeat 403 |
| POST admin enrollment-window `{ "enabled": true, "ttlMinutes": 30 }` | open |

- [x] **Step 2: Implement enroll router WITHOUT `require_device`**
- [x] **Step 3: Admin endpoints + minimal HTMX/form on devices page** (+ device detail revoke)
- [x] **Step 4: `pytest tests/test_enroll_and_device_tokens.py -q` PASS + `pytest -q` regression**

---

### Task 5: Android ProvisionStore + EnrollClient (unit where possible)

**Files:**
- Create: `android/app/src/main/java/com/eldershield/data/ProvisionStore.kt`
- Create: `android/app/src/main/java/com/eldershield/data/remote/EnrollClient.kt`
- Modify: `RuleSyncWorker` / `DeviceReportWorker` — read token from ProvisionStore keys (`device_api_key` key name kept for compat = token value)
- Modify: `build.gradle.kts` — `buildConfig = true`, `buildConfigField("String", "BASE_URL", ...)` from `eldershield.baseUrl` property; release empty default forces CI property

**Interfaces:**
- `ProvisionStore.hasToken(): Boolean`, `saveEnrollment(uuid, token, baseUrl)`, `deviceApiKey(): String?`, `baseUrl(): String`
- `EnrollClient.enroll(baseUrl, integrityToken, appVersion, model): EnrollResult`

- [x] Implement EncryptedSharedPreferences (androidx.security.crypto)
- [x] EnrollClient OkHttp POST JSON aliases camelCase
- [x] Workers unchanged API header: use stored token as `X-API-Key`

---

### Task 6: Release autoprovision + parent UX split

**Files:**
- Create: `android/app/src/main/java/com/eldershield/ui/Autoprovision.kt`
- Modify: `MainActivity.kt` — `if (BuildConfig.DEBUG)` show form; else run Autoprovision + permissions only; long-press title → admin CallScreening panel
- Add Play Integrity dependency; debug Autoprovision uses empty integrity + server skip

**Flow (release):**
1. Ensure `BuildConfig.BASE_URL` non-blank  
2. If no token → Integrity request (or empty when `BuildConfig.DEBUG`) → enroll  
3. Save token → enqueue workers  
4. Request runtime permissions  
5. CallScreening auto-request only if no peers and role empty (§1.2.1)

- [x] `:app:assembleDebug` succeeds  
- [x] Manual: lab with `ELDERSHIELD_ENROLL_SKIP_INTEGRITY=1` + window open → enroll → heartbeat (`scripts/lab-enroll-device.ps1`)

---

### Task 7: Runbooks + sprint index

**Files:**
- Modify: `docs/runbooks/play-internal.md`, `docs/runbooks/device-test.md`
- Modify: `docs/README.md` (plan link)
- Modify: `docs/plans/2026-11-20-phase2-sprint-board.md` or new thin board Status row for zero-touch

- [x] Add: “Play 설치 직전 관리자 **등록 창 ON** (기본 30분)”
- [x] Note: release AAB must set `eldershield.baseUrl=https://...` · no device key in binary

---

## Spec coverage self-review

| Spec item | Task |
|-----------|------|
| S1–S2 zero input / dual path | 5–6 |
| S3 no key in APK | 5–6 · buildConfig |
| S4 window OFF rejects | 2, 4 |
| S5 BD peer no steal | 6 (§1.2.1) |
| S6 revoke one device | 4 |
| Integrity MEETS_DEVICE_INTEGRITY | 2 |
| Admin UI window | 4 |
| Runbooks | 7 |

## Placeholder scan

None intentional. Google Integrity live decode may no-op fail-closed until credentials exist; tests use skip flag.

---

## Execution

Backend Tasks 1–4 first, then Android 5–6, then docs 7.  
User asked to proceed: start Task 1 in this session (inline), no auto-commit.
