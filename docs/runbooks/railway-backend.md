# Railway에 ElderShield Backend 배포

Zero-touch Play release는 **HTTPS** `eldershield.baseUrl`이 필요합니다.  
로컬 `127.0.0.1`은 Play/release cleartext 불가.

## 1. 프로젝트·서비스

1. Railway에서 프로젝트 생성 (예: `ElderShield`) 또는 GitHub `xzawed/ElderShield` 연결.  
2. 빌드 (Admin React SPA 포함 — **둘 중 하나**):
   - **권장 (SPA 자동 빌드)**: Root Directory **저장소 루트** (`/`) + 루트 `Dockerfile` (multi-stage: `node:20-alpine` → `admin-web` build → `backend/app/static/admin-spa`). 루트 `railway.toml` (`builder = DOCKERFILE`, `dockerfilePath = Dockerfile`). Start는 **셸 경유** 필수: `sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"`.
   - **기존 `/backend` 컨텍스트 유지 시**: `admin-web`은 Docker context 밖이므로 **배포 전** SPA를 커밋/산출물로 넣거나, Railway Build Command에서 `../admin-web` 빌드가 불가 — 대신 로컬·CI에서 `backend/scripts/build-admin-spa.sh` (또는 `cd admin-web && npm ci && npm run build`) 실행 후 이미지에 `backend/app/static/admin-spa/` 포함. GitHub Actions는 `admin-web` 빌드 후 pytest·아티팩트에 동일 경로 사용.
3. Volume: mount `/data` (sqlite 영속).  
4. Public domain 발급 (`*.up.railway.app`), healthcheck `/health`.  
   **현재 운영:** `https://eldershield.up.railway.app` (Admin: `/admin/ui/login`, GitHub About homepage와 동일).  
   **주의:** 도메인 `targetPort`는 컨테이너가 실제로 listen하는 `$PORT`와 같아야 함 (Railpack 기본 8080, Dockerfile 기본 8000). 불일치 시 외부 502.

## 2. 필수 변수

| 변수 | 값 |
|------|-----|
| `ADMIN_API_KEY` | 강한 관리자 키 (non `change-me`) |
| `DEVICE_API_KEY` | 랩/마이그레이션용 공유 키 (release 기기는 enroll 토큰 사용) |
| `DATABASE_URL` | 권장: `sqlite:////data/eldershield.db` (+ `/data` volume). Postgres도 가능 |
| `COOKIE_SECURE` | `1` |
| `PORT` | Railway가 주입 (보통 자동) |

**넣지 말 것 (프로덕션):** `ELDERSHIELD_ALLOW_INSECURE_DEFAULTS`, `ELDERSHIELD_ENROLL_SKIP_INTEGRITY`

## 3. Play Integrity (프로덕션 enroll)

| 변수 | 값 |
|------|-----|
| `PLAY_INTEGRITY_ENABLED` | `1` |
| `PLAY_PACKAGE_NAME` | `com.eldershield` |
| `GOOGLE_APPLICATION_CREDENTIALS` | 서비스 계정 JSON 경로 또는 Railway secret 파일 마운트 |
| (선택) | `pip` 이미지에 `requirements-integrity.txt` 포함하려면 Dockerfile에 추가 설치 |

## 4. Android AAB

```bash
cd android
./gradlew :app:bundleRelease \
  -Peldershield.baseUrl=https://eldershield.up.railway.app \
  -Peldershield.playCloudProjectNumber=YOUR_CLOUD_PROJECT_NUMBER
```

## 5. Admin SPA 로컬·CI 빌드

```bash
# repo root
cd admin-web && npm ci && npm run build
# → backend/app/static/admin-spa/index.html

# 또는
sh backend/scripts/build-admin-spa.sh
```

로컬 `uvicorn` 전에 위 빌드를 한 번 실행하면 `/admin/ui/`가 React shell을 제공합니다. 빌드 없으면 Jinja-only 경로만 동작하고 SPA pytest는 skip됩니다.

**Windows (운영 스모크):**

```powershell
powershell -File scripts/lab-admin-spa-smoke.ps1
# 기본 Base: https://eldershield.up.railway.app, 키: $env:TEMP\es-keys.json
```

## 6. 스모크

```bash
curl -s https://eldershield.up.railway.app/health
# Admin SPA: https://eldershield.up.railway.app/admin/ui/
# Devices → Open enrollment window → Play/Internal 설치
```

## 7. 로컬 DB 참고

랩 sqlite는 `backend/scripts/migrate_enroll_schema.py`로 컬럼 보강.  
프로덕션은 Postgres + `create_all`/마이그레이션 정책을 운영자가 고정.
