# Admin React SPA Dashboard — 설계

**상태:** Approved — Phase A 구현 계획 작성됨  
**일자:** 2026-11-21  
**관련:** 기존 Jinja Admin UI (`backend/app/web/admin_ui.py`), API `/api/v1/admin/*`  
**제품 URL:** `https://eldershield.up.railway.app/admin/ui/login`  
**계획:** [`../plans/2026-11-21-admin-react-spa-phase-a-implementation.md`](../plans/2026-11-21-admin-react-spa-phase-a-implementation.md)

## 1. 목적

관리자 콘솔을 스켈레톤 CRUD에서 **고급·정보 밀도 높은 운영 대시보드**로 전환한다.

확정 범위 (**C**):

- **홈 대시보드 신설** — 상태 KPI + 위협 패널 + 정책 요약
- **핵심 목록 페이지 요약 띠** — Devices / Restrictions / DNS 등
- **기능 유지** — 국가제한·call-rules·DNS·기기·Incident·allowlist·audit 전부 SPA로 이전(단계적)

확정 스택 (**안2 · R**):

- React 18 + Vite + TypeScript + React Router
- Tailwind (기존 brand teal / ink + Fraunces · Source Sans 3)
- 차트 1종 (Recharts 권장)
- 데이터: 기존 admin API + 세션 쿠키 (`credentials: 'include'`)

**비범위:** 부모님 Android UI, VpnService, 실시간 웹소켓(초기), 외부 BI.

## 2. 시각·UX 원칙

- 다크 사이드바 + 밝은 캔버스 (현 Jinja 구조 발전)
- 대시보드이므로 KPI/표/차트 조합 허용; 장식용 카드 남발 금지
- 상태 배지(정상/저하/위험), 밀도 있는 표, 미세 모션 2–3개(페이드, KPI 등장)
- **금지:** Inter/Roboto 기본 스택, 보라–인디고 AI 그라데이션, 과도한 glow, 이모지 장식
- ko/en: 쿠키 `es_admin_lang` 공유, 문자열 JSON 이식

## 3. 정보 구조 — 홈 `/admin/ui/`

| 구역 | 내용 |
|------|------|
| KPI 띠 | 전체 기기 · `protectionDegraded` · DNS 미설정 · CallScreening off |
| 위협 | 최근 Incident 표, 고위험 스캔 요약; 행 클릭 → device/incident |
| 차트 | 정상 vs 저하 도넛; 최근 Incident(또는 sync) 막대 |
| 정책 | 제한 국가 수 · denylist TLD 수 · rules/bundle version · enrollment window ON/OFF |

## 4. 라우트 · API 매핑

Base path: `/admin/ui/` (Vite `base: '/admin/ui/'`).

| 경로 | 화면 | API (대표) |
|------|------|------------|
| `/login` | 로그인 | 기존 admin UI login POST / 세션 |
| `/` | Dashboard | devices, incidents 집계, scans, restrictions, dns-denylist, health/rules, enrollment-window |
| `/devices` | 목록 + 요약 띠 | `GET /api/v1/admin/devices` |
| `/devices/:uuid` | 상세 · 스캔 · Incident · export | device, scans, incidents, export |
| `/restrictions` | CRUD + 요약 | country-restrictions |
| `/call-rules` | CRUD | call-rules |
| `/dns` | denylist + NextDNS sync | dns-denylist, sync-nextdns |
| `/allowlist` | CRUD | allowlist |
| `/audit` | 감사 | audit |

401 → `/login`.

## 5. 레포 · 빌드 · 배포

| 항목 | 결정 |
|------|------|
| 소스 | 레포 루트 `admin-web/` |
| 빌드 산출 | `backend/app/static/admin-spa/` (`npm run build` outDir) |
| FastAPI | `/admin/ui` 및 `/admin/ui/{path}` → SPA `index.html` fallback; `/api/v1` 기존 유지 |
| Railway | backend 이미지/빌드 단계에서 `admin-web` npm build 포함 또는 CI artifact 복사 |
| 로컬 | Vite dev + proxy → `http://127.0.0.1:8765` |

## 6. 마이그레이션 단계

| Phase | 내용 | 성공 기준 |
|-------|------|-----------|
| **A** | 셸·로그인·Dashboard·Devices 읽기 | 홈에 KPI·위협·정책 실데이터; Devices SPA; 스켈레톤 해소 |
| **B** | Restrictions, call-rules, DNS, allowlist, audit, device detail/Incident | 기존 Jinja CRUD와 동등 기능 |
| **C** | Jinja 템플릿 deprecate (필요 시 login만 잔존) | 단일 SPA 콘솔 |

Phase A에서 미이관 메뉴는 사이드바에서 旧 Jinja 경로 임시 링크 허용.

## 7. 백엔드 보완 (필요 시)

Dashboard 집계가 N+1이면 `GET /api/v1/admin/dashboard/summary` 추가 검토 (Phase A에서 클라이언트 집계로 시작 가능).

## 8. 자기검토

| 점검 | 결과 |
|------|------|
| §1–§2 반영 | React·C범위·KPI/위협/정책·빌드 경로 명시 |
| SSOT 충돌 | 관리자 전용 UI; 부모 UX·VpnService 무관 |
| 플레이스홀더 | Phase A/B/C로 범위 분할 |
| 구 도메인 | 운영 URL `eldershield.up.railway.app` 기준 |

## 9. 다음 단계

Phase A 구현 계획 승인·실행 → Phase B/C 별도 계획.
