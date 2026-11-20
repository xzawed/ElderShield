# Play Console — 계정 인증 대기 중에도 할 일

계정/개발자 인증이 끝나 **앱 만들기**가 열리기 전까지의 병행 작업입니다.

## 지금 가능한 것

| 우선 | 작업 | 결과물 |
|------|------|--------|
| 1 | **실기기 사이드로드 검증** | Play 없이 보호 기능 확인 ([아래 §1](#1-play-없이-설치release-경로)) |
| 2 | **Data safety / 권한 초안 확정** | Console 설문 복붙용 ([§2](#2-data-safety--권한-초안)) |
| 3 | **개인정보처리방침 URL 준비** | GitHub raw/blob URL ([`privacy-policy.md`](../legal/privacy-policy.md)) |
| 4 | **스토어 문구·스크린샷 초안** | 인증 직후 붙여넣기 ([§3](#3-스토어-리스팅-초안)) |
| 5 | (선택) Admin notify webhook | `ADMIN_NOTIFY_WEBHOOK_URL` |
| 6 | (선택) 부모님 Private DNS | `{profile}.dns.nextdns.io` — [`nextdns-setup.md`](nextdns-setup.md) |

## 지금 못 하는 것

- Play Console **앱 생성** / Internal testing 트랙 / 테스터 링크  
- Play App Signing에 업로드 키 등록 (앱 생성 이후)

인증 완료 후: [`play-internal.md`](play-internal.md) + 로컬  
`android/app/build/outputs/bundle/release/app-release.aab`

---

## 1. Play 없이 설치(release 경로)

서명된 AAB가 있으면 APKs로 뽑아 기기에 설치할 수 있습니다.

```powershell
cd F:\DEVELOPMENT\SOURCE\GROK\ElderShield\android
# bundletool 필요: https://github.com/google/bundletool/releases
java -jar bundletool.jar build-apks `
  --bundle=app\build\outputs\bundle\release\app-release.aab `
  --output=app-release.apks `
  --ks=upload-keystore.jks `
  --ks-pass=pass:YOUR_STORE_PASS `
  --ks-key-alias=upload `
  --key-pass=pass:YOUR_KEY_PASS
java -jar bundletool.jar install-apks --apks=app-release.apks
```

또는 빠른 랩용(클리어텍스트 LAN):

```powershell
.\gradlew.bat :app:assembleDebug
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

이후 [`device-test.md`](device-test.md) 체크리스트.

---

## 2. Data safety / 권한 초안

ElderShield는 **관리자 제어 방어 앱**. 부모 기기에서 수집·전송하는 것은 최소화합니다.

| 항목 | 제안 답 |
|------|---------|
| 데이터 수집 | 예 — 앱 기능 제공 |
| 수집 예시 | 기기 식별자(앱 생성 UUID), 앱 버전, Private DNS 설정 **여부/유형**, CallScreening 역할 보유 여부, 설치된 앱 중 **위험 판정 패키지명·권한 힌트**, 규칙 버전 |
| 수집하지 않음 | 정확한 위치, 연락처 원문, SMS 본문, 사진, 마이크, 광고 ID 판매 |
| 전화번호 | 차단 판단은 기기 로컬; 서버에 **원문 번호 저장 안 함** |
| 암호화 | 전송 중: HTTPS 권장(필수 운영). 저장: 서버 DB는 운영자 관리 |
| 제3자 공유 | 광고 SDK 없음. NextDNS는 **운영자가 설정한 DNS 정책** (앱이 사용자 트래픽을 NextDNS 계정으로 판매하지 않음) |
| 계정 | 기기 API 키로 등록 — 소셜 로그인 없음 |
| 삭제 요청 | 관리자가 백엔드에서 기기/스캔 행 삭제 + 앱 제거 |

### Manifest 권한(예상 선언)

| 권한/역할 | 목적 |
|-----------|------|
| `ROLE_CALL_SCREENING` | 수신 위험 국가 차단 (보유 시에만) |
| 인터넷 | 규칙 sync / heartbeat / 스캔 보고 |
| 패키지 목록 조회 | 사이드로드·오버레이 **가능 앱** 보고 |
| (해당 시) 기타 최소 권한 | 배터리 최적화 예외 등은 사용 시만 |

---

## 3. 스토어 리스팅 초안

**짧은 설명 (80자 내외)**  
부모님 폰의 위험 국가 전화·웹과 사기성 앱 징후를 관리자만 조용히 지키는 방어 앱.

**긴 설명**  
ElderShield(실버실드)는 기술에 익숙하지 않은 가족을 위해 설계된 방어 전용 앱입니다.  
설치와 권한 허용 후 부모님은 추가 조작이 없습니다. 관리자만 웹에서 국가 제한·화이트리스트·기기 상태를 봅니다.  
Bitdefender 등 기존 보안 앱과 병행할 수 있으며, 은행 앱을 위해 VPN/오버레이/접근성 서비스는 사용하지 않습니다.

**카테고리**  
도구 / 생산성 (또는 보안 — Console 옵션에 맞게)

**스크린샷 (인증 후 촬영)**  
1. Admin UI 로그인  
2. Country restrictions  
3. Devices (health)  
4. (선택) 앱 최소 설치 화면 — 부모 UI는 상태 노출 최소화

---

## 4. 인증 완료 직후 체크

1. 앱 생성 → Internal testing  
2. `app-release.aab` 업로드  
3. Data safety / 개인정보처리방침 URL 붙여넣기  
4. 테스터 이메일 + 설치 링크  
5. HTTPS 백엔드로 프로비저닝 → Devices heartbeat 확인
