# RCA: 에뮬 “외국번호로 걸기”를 ‘불가/무관’으로 본 논리 오류

## 잘못된 판단
1. “한국에 CN SIM 없음 → 외국번호 통화 시나리오 재현 곤란”으로 좁혀 해석함.  
2. SSOT 문구 “발신은 플랫폼이 CallScreening으로 넘기지 않음”을 **사실**로 취급함.  
3. 사용자가 에뮬 **내 번호**를 외국으로 바꾼 뒤 걸 수 있다고 했을 때, ‘차단 테스트가 아니다’만 강조하고 **재현 수단(`phonenumber` / `gsm call`) 자체는 가능하다**는 계획을 누락함.

## 실제
| 수단 | 역할 |
|------|------|
| `adb emu phonenumber 8613…` | AVD **내 회선 번호** 설정 (`+` 붙이면 KO) |
| `adb emu gsm call +8613…` | **수신** CLI 주입 → 국가 차단 정본 테스트 |
| 다이얼러/`CALL` 인텐트 | **발신** — 플랫폼도 `onScreenCall` 호출(dir=1). SSOT는 국가 차단 **하지 않음** |

## 구현 오류 (함께 발견)
`ElderCallScreeningService`가 direction을 무시해 **발신 CN 목적지도 Reject** 함 → SSOT §6.1 위반.  
수정: `CallScreeningDecision`이 `DIRECTION_INCOMING`일 때만 country-block (UT-A-26).

## 검증 (2026-11-19)
- E0 `phonenumber 8613999000001` → OK  
- E2 발신 `+8613…` → `dir=1 block=false`  
- E3 수신 `gsm call +8613…` → `dir=0 block=true` Reject  
- E1 내번호 CN + 발신 114 → `dir=1 block=false`
