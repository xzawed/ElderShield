# Admin React SPA Dashboard — 설계

**상태:** Phase A + 로그 가시화(L1–L3) + **주 네비 셸 통일** 반영 · CRUD 폼은 Phase B 잔여  
**일자:** 2026-11-21  
**관련:** Jinja Admin UI (`backend/app/web/admin_ui.py`), API `/api/v1/admin/*`  
**제품 URL:** `https://eldershield.up.railway.app/admin/ui/`  
**계획:** [`../plans/2026-11-21-admin-react-spa-phase-a-implementation.md`](../plans/2026-11-21-admin-react-spa-phase-a-implementation.md) · 로그 [`2026-11-21-admin-log-visibility-design.md`](2026-11-21-admin-log-visibility-design.md)

## 1. 목적

관리자 콘솔을 스켈레톤 CRUD에서 **고급·정보 밀도 높은 운영 대시보드**로 전환한다.

확정 범위 (**C**):

- **홈 대시보드** — 상태 KPI + 위협 패널 + 정책 요약
- **핵심 목록** — Devices / Restrictions / Call rules / DNS denylist / Allowlist / Audit / DNS logs
- **기능 유지** — CRUD는 단계적 SPA 이전; 목록·조회는 SPA, 생성·편집 폼은 당분간 Jinja

확정 스택 (**안2 · R**): React 18 + Vite + TS + React Router · Tailwind · Recharts · 세션 쿠키 + `X-ElderShield-Admin: 1`

**비범위:** 부모님 Android UI, VpnService, 실시간 웹소켓(초기), 외부 BI.

## 2. 하드 UX 불변식 — 셸 통일

- **주 사이드바 메뉴 이동 시 SPA `AdminShell`이 바뀌면 안 된다** (Jinja `base.html`로 전체 리로드 금지).
- 주 목록 GET 경로(`SPA_SHELL_SEGMENTS`)는 모두 동일 `index.html`을 반환한다.
- Jinja는 **폼·레거시 상세**만: `/restrictions/new`, `/restrictions/{id}`, call-rules/allowlist 생성·삭제 폼 등.
- Jinja `base.html` 네비 링크도 SPA 목록 경로를 가리켜, 폼에서 나가면 React 셸로 복귀한다.
- 검증: `tests/test_admin_spa_static.py` (세그먼트 집합 + `id="root"`) · `scripts/lab-admin-spa-smoke.ps1` (`spa-nav-shell-unity`).

## 3. 시각·UX 원칙

- 다크 사이드바 + 밝은 캔버스
- KPI/표/차트 조합 허용; 장식용 카드 남발 금지
- **금지:** Inter/Roboto 기본 스택, 보라–인디고 AI 그라데이션, 과도한 glow, 이모지
- ko/en: 쿠키 `es_admin_lang` 공유

## 4. 라우트 · API 매핑

Base: `/admin/ui/` (Vite `base: '/admin/ui/'`).

| 경로 | 화면 | 셸 | API (대표) |
|------|------|-----|------------|
| `/login` | 로그인 | SPA | `POST /admin/ui/api/login` |
| `/` | Dashboard | SPA | devices, incidents, restrictions, dns-denylist, health, enrollment |
| `/devices` | 목록 | SPA | `GET /devices` |
| `/devices/:uuid` | 상세 · revoke | SPA | device, health, scans, DELETE token |
| `/incidents/:id` | Incident | SPA | export / incidents |
| `/audit` | 감사 | SPA | audit |
| `/dns-logs` | NextDNS 질의 | SPA | `GET /dns-logs` |
| `/restrictions` | 목록(읽기) | SPA | country-restrictions |
| `/call-rules` | 목록(읽기) | SPA | call-rules |
| `/dns-denylist` | denylist 요약 | SPA | dns-denylist |
| `/allowlist` | 목록(읽기) | SPA | app-allowlist |
| `/restrictions/new` · `/{id}` 등 | CRUD 폼 | **Jinja** | form POST |

401(API) → `/login`.

## 5. 레포 · 빌드 · 배포

| 항목 | 결정 |
|------|------|
| 소스 | `admin-web/` |
| 빌드 산출 | `backend/app/static/admin-spa/` (gitignore; Docker/CI에서 빌드) |
| FastAPI | `spa.py` exact segments + param routes; Jinja 폼 경로 공존 |
| Railway | 루트 Dockerfile multi-stage npm build |

## 6. 마이그레이션 단계

| Phase | 내용 | 상태 |
|-------|------|------|
| **A** | 셸·로그인·Dashboard·Devices 목록 | Done (PR #18) |
| **A′** | 로그 가시화 L1–L3 | Done (PR #21) |
| **A″** | 주 네비 셸 통일 + 정책 목록 SPA 읽기 | Done (PR #22) |
| **B** | Restrictions/call-rules/DNS/allowlist **CRUD를 SPA 폼으로** | Open |
| **C** | Jinja 템플릿 deprecate | Open |

## 7. 자기검토

| 점검 | 결과 |
|------|------|
| 셸 통일 | 주 메뉴 `Link` only; Jinja 목록 GET은 SPA가 선점 |
| SSOT | 관리자 전용; 부모 UX·VpnService 무관 |
| 검증 공백 교훈 | HTTP/`id="root"`만으로는 사이드바 연속성 미검증 → 스모크에 nav 연속성 필수 |

## 8. 다음 단계

Phase B: 정책 CRUD를 SPA 폼으로 옮겨 Jinja 셸 잔여를 제거.
