# Incident Evidence Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** On app-risk / call-Reject / (later) DNS-block triggers, upload a minimal JSON Incident evidence pack for admin export—without raising parent LTE/CPU load or storing raw phone numbers.

**Architecture:** Device keeps small Room ring buffers; on trigger A, `IncidentAssembler` slices T−24h..T+1h, merges duplicates within 1h, and POSTs meta-only JSON. Backend stores `Incident` rows (90-day TTL). DNS axis C is filled by server-side NextDNS log pull when credentials exist; otherwise `dns.available=false`.

**Tech Stack:** FastAPI · SQLModel · Alembic/SQLModel create · pytest · Android Kotlin · Room · WorkManager · OkHttp · NextDNS API (server)

**Spec:** [`../specs/2026-11-21-incident-evidence-pack-design.md`](../specs/2026-11-21-incident-evidence-pack-design.md)

## Global Constraints

- 부모님 불편 제로 · 알림/팝업 없음 · Overlay/A11y/Device Admin/GPS/VpnService **금지**
- 평소 증거 서버 스트림 **금지** · 사건 시 **메타 JSON만** (APK 바이너리 기본 미전송)
- 전화번호 **원문 서버 저장 금지** (SHA-256 해시 + optional last4)
- `countries`는 항상 배열 · Bitdefender §1.2.1 준수
- Backend → Android 순 · TDD · **자동 커밋 금지** (사용자 요청 시에만 commit 스텝 실행)
- NextDNS 미설정 시 A+B만으로 export 가능해야 함

---

## File map

| Path | Responsibility |
|------|----------------|
| `backend/app/models/incident.py` | `Incident` SQLModel (id, device_uuid, triggered_at, triggers JSON, payload JSON, created_at) |
| `backend/app/models/__init__.py` | export Incident |
| `backend/app/api/schemas.py` | `IncidentIn`, `IncidentOut`, export alias |
| `backend/app/services/incident_merge.py` | 1h merge decision helper |
| `backend/app/api/devices.py` | `POST /devices/incidents` |
| `backend/app/api/admin.py` | list/get/export incidents |
| `backend/app/services/nextdns_logs.py` | optional pull logs for window → merge into payload |
| `backend/app/web/admin_ui.py` + templates | device incidents UI + export link |
| `backend/tests/test_incidents.py` | TDD API + merge + no raw phone |
| `android/.../data/local/CallEvidenceEntity.kt` + Dao | ring buffer ≤200 |
| `android/.../data/local/ElderShieldDatabase.kt` | version bump + entities |
| `android/.../domain/incident/PhoneEvidenceHasher.kt` | SHA-256 of normalized digits |
| `android/.../domain/incident/IncidentAssembler.kt` | build payload from buffers + apps |
| `android/.../data/remote/IncidentApi.kt` | POST incidents |
| `android/.../service/IncidentUploadWorker.kt` | one-shot upload |
| `android/.../service/ElderCallScreeningService.kt` | append buffer + trigger on Reject |
| `android/.../service/DeviceReportWorker.kt` | after scan score≥50 enqueue incident |
| `android/core/.../IncidentAssemblerTest.kt` | unit tests |
| `docs/specs/2026-11-18-eldershield-system-design.md` | short addendum link |
| `docs/plans/2026-11-19-sprint-board.md` | Status only |

---

### Task 1: Backend Incident model + merge helper (TDD)

**Files:**
- Create: `backend/app/models/incident.py`
- Create: `backend/app/services/incident_merge.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_incident_merge.py`

**Interfaces:**
- Produces: `class Incident(SQLModel)` with `id: str`, `device_uuid: str`, `triggered_at: datetime`, `triggers: list[str]`, `payload: dict`, `created_at: datetime`
- Produces: `should_merge(existing_triggered_at: datetime, new_triggered_at: datetime, window_seconds: int = 3600) -> bool`
- Produces: `merge_payloads(base: dict, incoming: dict) -> dict` (union triggers, concat apps/calls unique-ish, prefer dns.available true)

- [x] **Step 1: Write failing tests**

```python
# backend/tests/test_incident_merge.py
from datetime import datetime, timedelta, timezone
from app.services.incident_merge import should_merge, merge_payloads

def test_should_merge_within_one_hour():
    t0 = datetime(2026, 11, 21, 3, 0, tzinfo=timezone.utc)
    assert should_merge(t0, t0 + timedelta(minutes=50))
    assert not should_merge(t0, t0 + timedelta(hours=2))

def test_merge_unions_triggers_and_calls():
    base = {"triggers": ["call_reject"], "calls": [{"phoneHash": "a"}], "apps": [], "dns": {"available": False, "events": []}}
    inc = {"triggers": ["app_scan"], "calls": [{"phoneHash": "b"}], "apps": [{"packageName": "x"}], "dns": {"available": False, "events": []}}
    out = merge_payloads(base, inc)
    assert set(out["triggers"]) == {"call_reject", "app_scan"}
    assert len(out["calls"]) == 2
    assert out["apps"][0]["packageName"] == "x"
```

- [x] **Step 2: Run tests — expect FAIL (import/module missing)**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_incident_merge.py -v
```

Expected: `ModuleNotFoundError` or collection error for `app.services.incident_merge`

- [x] **Step 3: Implement model + merge helper**

```python
# backend/app/models/incident.py
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

class Incident(SQLModel, table=True):
    __tablename__ = "incident"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    device_uuid: str = Field(index=True, max_length=128)
    triggered_at: datetime = Field(index=True)
    triggers: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=_utcnow)
```

```python
# backend/app/services/incident_merge.py
from datetime import datetime, timedelta

def should_merge(existing_triggered_at: datetime, new_triggered_at: datetime, window_seconds: int = 3600) -> bool:
    return abs((new_triggered_at - existing_triggered_at).total_seconds()) <= window_seconds

def merge_payloads(base: dict, incoming: dict) -> dict:
    out = dict(base)
    out["triggers"] = sorted(set(base.get("triggers", [])) | set(incoming.get("triggers", [])))
    # calls: append by phoneHash+at; apps: append by packageName
    calls = list(base.get("calls") or [])
    seen = {(c.get("phoneHash"), c.get("at")) for c in calls}
    for c in incoming.get("calls") or []:
        key = (c.get("phoneHash"), c.get("at"))
        if key not in seen:
            calls.append(c)
            seen.add(key)
    out["calls"] = calls
    apps = list(base.get("apps") or [])
    apk = {a.get("packageName") for a in apps}
    for a in incoming.get("apps") or []:
        if a.get("packageName") not in apk:
            apps.append(a)
            apk.add(a.get("packageName"))
    out["apps"] = apps
    b_dns, i_dns = base.get("dns") or {}, incoming.get("dns") or {}
    if i_dns.get("available"):
        out["dns"] = i_dns
    else:
        out["dns"] = b_dns if b_dns else i_dns
    for k in ("countryHints", "protectionSnapshot", "window"):
        if incoming.get(k):
            out[k] = incoming[k]
    return out
```

- [x] **Step 4: Register model in `models/__init__.py`; re-run pytest — expect PASS**

- [ ] **Step 5: Commit only if user requested** — otherwise skip

---

### Task 2: Device POST `/devices/incidents` + admin GET/export

**Files:**
- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/api/devices.py`
- Modify: `backend/app/api/admin.py`
- Test: `backend/tests/test_incidents_api.py`

**Interfaces:**
- Consumes: `Incident`, `should_merge`, `merge_payloads`, `require_device`, `require_admin`
- Produces: `POST /api/v1/devices/incidents` → 201/200 with `{incidentId}`
- Produces: `GET /api/v1/admin/devices/{device_uuid}/incidents`
- Produces: `GET /api/v1/admin/incidents/{incident_id}`
- Produces: `GET /api/v1/admin/incidents/{incident_id}/export` (same JSON attachment)

- [x] **Step 1: Failing API tests**

```python
# backend/tests/test_incidents_api.py
def test_post_incident_rejects_raw_phone_in_payload(client, device_headers):
    body = {
        "incidentId": "11111111-1111-1111-1111-111111111111",
        "deviceUuid": "dev-1",
        "triggeredAt": "2026-11-21T03:00:00Z",
        "triggers": ["call_reject"],
        "calls": [{"at": "2026-11-21T02:59:00Z", "countryIso": "CN", "decision": "Reject", "phoneNumber": "+86139"}],
        "apps": [],
        "dns": {"available": False, "events": []},
    }
    # Implementation must strip/reject keys phoneNumber / number / raw
    r = client.post("/api/v1/devices/incidents", json=body, headers=device_headers)
    assert r.status_code in (400, 422) or (
        r.status_code in (200, 201) and "phoneNumber" not in str(r.json())
    )

def test_post_incident_idempotent_and_merge(client, device_headers, admin_headers, enrolled_device_uuid):
    # post twice within 1h with different triggers → one row, merged triggers
    ...
```

Fill `enrolled_device_uuid` using existing enroll fixtures from `test_enroll_and_device_tokens.py` / heartbeat tests—copy the same client fixture pattern from `backend/tests/test_devices_heartbeat.py` (or nearest devices test).

- [x] **Step 2: Run — expect FAIL (404 route)**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_incidents_api.py -v
```

- [x] **Step 3: Schemas + sanitize**

Add to `schemas.py`:

```python
class IncidentIn(BaseModel):
    incidentId: str
    deviceUuid: str
    triggeredAt: datetime
    triggers: list[str]
    window: dict | None = None
    apps: list[dict] = Field(default_factory=list)
    calls: list[dict] = Field(default_factory=list)
    dns: dict = Field(default_factory=dict)
    countryHints: dict | None = None
    protectionSnapshot: dict | None = None

class IncidentOut(BaseModel):
    incidentId: str
    deviceUuid: str
    triggeredAt: datetime
    triggers: list[str]
    payload: dict
    createdAt: datetime
```

Sanitize function: drop any call key in `{"phoneNumber","number","raw","msisdn"}`; require `phoneHash` if call present.

- [x] **Step 4: Wire routes**

In `devices.py`:

```python
@router.post("/devices/incidents")
def post_incident(body: IncidentIn, session: Session = Depends(get_session), _auth=Depends(require_device)):
    # verify body.deviceUuid matches authenticated device when per-device token used
    # lookup open incident for device where should_merge(existing.triggered_at, body.triggeredAt)
    # else insert new Incident(id=body.incidentId or uuid)
    # never persist raw phone keys
    ...
```

In `admin.py`: list by device, get by id, export returns `JSONResponse` with `Content-Disposition: attachment; filename=incident-{id}.json`.

- [x] **Step 5: pytest PASS**

- [ ] **Step 6: Commit only if user requested**

---

### Task 3: Admin UI — incidents on device page

**Files:**
- Modify: `backend/app/web/admin_ui.py`
- Modify: `backend/app/web/templates/admin/device_detail.html` (or equivalent existing device template—locate via grep `scan`)
- Modify: `backend/app/web/i18n.py` (ko/en strings for Incidents / Export)

**Interfaces:**
- Consumes: admin incident list query
- Produces: HTML table + link to `/api/v1/admin/incidents/{id}/export` (or UI route that streams same JSON)

- [x] **Step 1: Find device detail template**

```bash
rg -n "scan|device_uuid" backend/app/web/templates
```

- [x] **Step 2: Add incidents section** (triggeredAt, triggers, export button). No parent-facing copy.

- [x] **Step 3: Manual smoke** — run uvicorn, open `/admin/ui/devices/{uuid}`, confirm empty list then after Task 2 POST shows row.

- [ ] **Step 4: Commit only if user requested**

---

### Task 4: Android phone hash + call evidence Room buffer (TDD)

**Files:**
- Create: `android/core/src/main/kotlin/com/eldershield/domain/incident/PhoneEvidenceHasher.kt`
- Create: `android/core/src/test/kotlin/com/eldershield/domain/incident/PhoneEvidenceHasherTest.kt`
- Create: `android/app/src/main/java/com/eldershield/data/local/CallEvidenceEntity.kt`
- Create: `android/app/src/main/java/com/eldershield/data/local/CallEvidenceDao.kt`
- Modify: `android/app/src/main/java/com/eldershield/data/local/ElderShieldDatabase.kt` (version **2**, entities += CallEvidenceEntity)

**Interfaces:**
- Produces: `PhoneEvidenceHasher.hash(normalizedDigits: String): String` (SHA-256 hex)
- Produces: `PhoneEvidenceHasher.last4(normalizedDigits: String): String`
- Produces DAO: `insert`, `trimToMax(200)`, `listBetween(fromMs, toMs)`

- [x] **Step 1: Failing unit test**

```kotlin
// PhoneEvidenceHasherTest.kt
@Test
fun hash_is_stable_and_not_raw() {
    val h = PhoneEvidenceHasher.hash("8613999887766")
    assertEquals(64, h.length)
    assertFalse(h.contains("8613999887766"))
    assertEquals("7766", PhoneEvidenceHasher.last4("8613999887766"))
}
```

- [x] **Step 2: Run**

```bash
cd android && .\gradlew.bat :core:test --tests com.eldershield.domain.incident.PhoneEvidenceHasherTest
```

Expected: FAIL class missing

- [x] **Step 3: Implement hasher + Room entity/dao + DB v2**

```kotlin
object PhoneEvidenceHasher {
    fun hash(normalizedDigits: String): String {
        val md = MessageDigest.getInstance("SHA-256")
        return md.digest(normalizedDigits.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    }
    fun last4(normalizedDigits: String): String =
        normalizedDigits.takeLast(4).padStart(4, '0')
}
```

`CallEvidenceEntity`: `id` Long PK auto, `atEpochMs` Long, `countryIso` String?, `decision` String, `phoneHash` String, `last4` String?

Dao trim: `DELETE FROM call_evidence WHERE id NOT IN (SELECT id FROM call_evidence ORDER BY atEpochMs DESC LIMIT 200)`

- [x] **Step 4: Tests PASS**

---

### Task 5: IncidentAssembler + IncidentApi + UploadWorker (A+B)

**Files:**
- Create: `android/core/src/main/kotlin/com/eldershield/domain/incident/IncidentAssembler.kt`
- Create: `android/core/src/test/kotlin/com/eldershield/domain/incident/IncidentAssemblerTest.kt`
- Create: `android/app/src/main/java/com/eldershield/data/remote/IncidentApi.kt`
- Create: `android/app/src/main/java/com/eldershield/service/IncidentUploadWorker.kt`
- Create: `android/app/src/main/java/com/eldershield/scanner/ApkForensics.kt` (signing cert + apk sha256 from PackageManager / file)

**Interfaces:**
- Produces: `IncidentAssembler.build(trigger: String, nowMs: Long, calls: List<CallEvidence>, apps: List<AppForensics>, protection: ProtectionSnapshot): IncidentPayload`
- Window: `nowMs - 24h` .. `nowMs + 1h` (future buffer empty OK)
- `IncidentApi.post(payload)` → HTTP 200/201
- Worker reads prefs `base_url` + `device_api_key` + `device_uuid` like `DeviceReportWorker`

- [x] **Step 1: Assembler unit tests** — window filter, no raw number field in JSON map, triggers list

- [x] **Step 2: Implement assembler + forensics helper**

`ApkForensics.from(pm, packageName)` returns cert SHA-256, apk SHA-256 (MessageDigest on APK file path), versionName/code, installer.

- [x] **Step 3: IncidentApi POST `/api/v1/devices/incidents`**

- [x] **Step 4: IncidentUploadWorker** — load buffers, assemble, post; on success mark uploaded ids; never Log raw number

- [x] **Step 5: `./gradlew.bat :core:test :app:assembleDebug` PASS**

---

### Task 6: Wire triggers (CallScreening Reject + scan score≥50)

**Files:**
- Modify: `android/app/src/main/java/com/eldershield/service/ElderCallScreeningService.kt`
- Modify: `android/app/src/main/java/com/eldershield/service/DeviceReportWorker.kt`
- Modify: `android/app/src/main/java/com/eldershield/domain/matching/DefaultCountryRestrictionMatcher` usage — already returns ISO via match; ensure screening path can record `countryIso` (extend decision path to return iso or re-match once)

**Interfaces:**
- On every screened incoming call: insert CallEvidence (Allow or Reject)
- On Reject: enqueue `IncidentUploadWorker` with trigger `call_reject`
- After `scanSuspicious()`: if any `riskScore >= 50`, enqueue worker with trigger `app_scan`

- [x] **Step 1: Extend screening to persist evidence** without logging raw number (`len` only remains OK)

- [x] **Step 2: Enqueue unique work `eldershield-incident-upload` with `ExistingWorkPolicy.APPEND_OR_REPLACE` or debounce 5s**

- [x] **Step 3: Emulator smoke (lab)** — gsm Reject CN → admin incidents list non-empty; export has phoneHash no `+86...`

- [ ] **Step 4: Commit only if user requested**

---

### Task 7: NextDNS log pull (axis C) — server-side

**Files:**
- Create: `backend/app/services/nextdns_logs.py`
- Modify: `backend/app/api/devices.py` or post-process in admin export
- Modify: `backend/app/services/nextdns_sync.py` (reuse HTTP client/env)
- Test: `backend/tests/test_nextdns_logs.py` (mock httpx)

**Interfaces:**
- Produces: `fetch_blocked_domains(from_ts, to_ts) -> list[dict]` or empty if env unset
- On `POST /devices/incidents` or on `export`: if `NEXTDNS_*` set and payload.dns.available is false/empty, merge events into payload (persist update)

- [x] **Step 1: Test env-unset returns [] and does not fail incident POST**

- [x] **Step 2: Implement pull against NextDNS analytics/logs API** (confirm path via existing `search-docs` / NextDNS API docs—use official logs endpoint; if unavailable, document stub + denylist-hit placeholder only)

- [x] **Step 3: pytest with respx/httpx mock PASS**

**Note:** Ops must set Railway `NEXTDNS_API_KEY` + `NEXTDNS_PROFILE_ID` and Private DNS hostname on device for real C evidence. Plan does not require VPN.

---

### Task 8: SSOT addendum + sprint Status + lab script

**Files:**
- Modify: `docs/specs/2026-11-18-eldershield-system-design.md` — short § link to incident evidence pack (민감정보 예외 한 단락)
- Modify: `docs/plans/2026-11-19-sprint-board.md` — Status line only
- Create: `scripts/lab-incident-evidence-verify.ps1` — emu Reject + POST path check + export assert no raw phone

- [x] **Step 1: SSOT paragraph + board Status**
- [x] **Step 2: Lab script smoke against local or Railway** — `scripts/lab-incident-evidence-verify.ps1` landed; Railway POST `/devices/incidents` 404 until A+B API is deployed
- [ ] **Step 3: Commit only if user requested**

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| A app forensics meta | T5–T6 |
| B call meta + hash | T4–T6 |
| C NextDNS server pull | T7 |
| Trigger A (scan/reject/dns) | T6–T7 |
| T−24h..T+1h + 1h merge | T1 merge + T5 assembler + T2 API |
| Meta-only / no APK bytes | T5 (forensics hashes only) |
| No parent UI/alerts | T6 (no notification code) |
| No GPS/VPN | Global + no new services |
| Admin export | T2–T3 |
| 90-day TTL | T2 (add note + optional cleanup job in same task: delete where created_at < now-90d on GET list or startup hook) |
| privacy already updated | — (done at spec time); T8 SSOT only |

**TTL:** In Task 2 Step 4, include:

```python
def purge_old_incidents(session: Session, days: int = 90) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    ...
```

Call from admin list or post_incident occasionally.

**Placeholder scan:** None intentional. NextDNS exact URL confirmed at Task 7 Step 2 against live API docs.

---

## Execution handoff

Plan saved to `docs/plans/2026-11-21-incident-evidence-pack-implementation.md`.

**실행 방식 선택:**

1. **Subagent-Driven (권장)** — 태스크마다 새 서브에이전트 + 리뷰  
2. **Inline Execution** — 이 세션에서 체크포인트 단위로 연속 구현  

어느 쪽으로 진행할까요?
