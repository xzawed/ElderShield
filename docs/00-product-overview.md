# 00. 제품 개요

**SSOT 설계**: [`specs/2026-11-18-eldershield-system-design.md`](specs/2026-11-18-eldershield-system-design.md)

## 한 줄

ElderShield(실버실드)는 부모님 Android 기기의 **위험 국가 전화·인터넷 접근을 차단**하고 **출처 불명/사기 앱을 탐지**하는 방어적 Guard다. 관리자만 웹으로 규칙을 제어하고, 부모님은 설치·권한 후 조작이 없다.

## 목적

- 위험 국가 전화·인터넷 접근 차단
- 이미 설치된 출처 불명/사기 앱 탐지 → 관리자 보고
- 관리자 전용 웹 대시보드
- Bitdefender와 병행 (1차 방어) — SSOT §1.2.1: CallScreening 역할 강탈·BD 끄기 지시 금지. 역할 미보유 시 전화 차단만 비활성, DNS/스캔 유지

## 하드 제약

| 제약 | 상세 |
|------|------|
| 부모님 불편 제로 | 설치·권한 후 추가 조작 없음. 알림/팝업 최소화 |
| 은행 앱 호환 | VpnService 기본 비활성. Overlay/Accessibility/Device Admin 금지 |
| 무인지 업데이트 | 규칙·앱 업데이트 시 부모님 화면에 표시 없음 |
| 합법적 방어만 | 역공격·강제 삭제·불법 행위 없음 |
| 리소스 최소 | 배터리·WorkManager 제약 준수 |
| 다중 국가 유지 | 제한 국가 리스트는 다중 선택·지속 관리 |

## 대상 기기

- 부모님: Galaxy Note 10+ (Android 12 기준), Galaxy Tab S5e / Tab 6
- 테스트: Galaxy S22 Ultra, Galaxy Tab 6
- minSdk: 29 (Android 10)

## Phase 1 / 2

- **Phase 1**: Call screening(수신 전용 국가 차단), Private DNS 모니터, DNS denylist + **NextDNS sync API**(운영 키 필요), AppScanner 보고, Admin CRUD
- **Phase 2 (C→A)**: 기기 health · 오버레이/사기팝업 **가능 앱** 탐지(P3) · phishing/scam-ad DNS 피드 · role_lost 경보 → 이어서 audit/notify/메트릭/auth. 상세: [`specs/2026-11-20-phase2-ac-depth-quality-design.md`](specs/2026-11-20-phase2-ac-depth-quality-design.md)
- **후순위**: VpnService IP 필터(은행앱 회귀 후), B 다조직  
  (NextDNS **운영 프로필·키 실배포**는 Phase 1 코드 경로 위 운영자 게이트)
