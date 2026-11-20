# Railway에 ElderShield Backend 배포

Zero-touch Play release는 **HTTPS** `eldershield.baseUrl`이 필요합니다.  
로컬 `127.0.0.1`은 Play/release cleartext 불가.

## 1. 프로젝트·서비스

1. Railway에서 프로젝트 생성 (예: `ElderShield`) 또는 GitHub `xzawed/ElderShield` 연결.  
2. 빌드 (둘 중 하나):
   - **권장**: Root Directory `/backend` + Railpack (현재 `main`에 Dockerfile 없어도 동작). Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
   - **대안**: 저장소 루트 `Dockerfile` + `railway.toml` (`builder = DOCKERFILE`).
3. Volume: mount `/data` (sqlite 영속).  
4. Public domain 발급 (`*.up.railway.app`), healthcheck `/health`.

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
  -Peldershield.baseUrl=https://YOUR-SERVICE.up.railway.app \
  -Peldershield.playCloudProjectNumber=YOUR_CLOUD_PROJECT_NUMBER
```

## 5. 스모크

```bash
curl -s https://YOUR-SERVICE.up.railway.app/health
# Admin UI: /admin/ui/login
# Devices → Open enrollment window → Play/Internal 설치
```

## 6. 로컬 DB 참고

랩 sqlite는 `backend/scripts/migrate_enroll_schema.py`로 컬럼 보강.  
프로덕션은 Postgres + `create_all`/마이그레이션 정책을 운영자가 고정.
