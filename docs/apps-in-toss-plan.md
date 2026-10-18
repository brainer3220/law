# Tesseract (law) Apps-in-Toss Plan — BRA-53

토스 앱 안에서 Tesseract를 미니앱(Apps-in-Toss)으로 제공한다. 참고: [앱인토스 바이브 코딩 영상](https://www.youtube.com/watch?v=SNOjrzGpUkQ), 팩트콕 선행 사례(kpn-factcheck).

## 범위 (이 스캐폴드 PR)

- `@apps-in-toss/web-bridge` 런타임 감지: 토스/샌드박스 런타임에서만 토스 로그인 UI 노출, 일반 웹은 기존 Supabase 인증 유지
- 토스 OAuth 로그인 스캐폴드:
  - `apps/web/lib/toss/tossAuth.ts` — authorizationCode 교환, mTLS API 호출, 서명된 세션 쿠키(`law_toss_session`, 14일)
  - `apps/web/app/api/auth/toss/login|logout|session/route.ts`
  - `apps/web/components/toss/TossLoginButton.tsx`
- 토스 세션은 Supabase 계정과 분리된 최소 세션(userKey만). 계정 연동/권한 매핑은 후속 작업.

## 환경 변수 (Vercel law 프로젝트에 설정 필요)

| 이름 | 용도 |
| --- | --- |
| `TOSS_MTLS_CERT_PEM` / `TOSS_MTLS_CERT_BASE64` | 토스 파트너 mTLS 인증서 |
| `TOSS_MTLS_KEY_PEM` / `TOSS_MTLS_KEY_BASE64` | mTLS 개인키 |
| `TOSS_MTLS_KEY_PASSPHRASE` | 개인키 암호 (있는 경우) |
| `TOSS_LOGIN_SESSION_SECRET` | 세션 쿠키 HMAC 서명 키 |

## 콘솔 등록 절차 (앱인토스 콘솔, 수동)

1. 토스 파트너스/앱인토스 콘솔에서 Tesseract 앱 생성 (서비스명 확정 필요)
2. 웹 앱 URL 등록: 프로덕션 도메인 (law-kappa.vercel.app 또는 커스텀 도메인)
3. mTLS 인증서 발급/등록 후 위 env를 Vercel에 설정
4. 샌드박스 런타임에서 로그인 플로우 검증
5. 심사 제출: 팩트콕의 `docs/apps-in-toss-review.md`와 같은 리뷰 노트 작성 (공개/로그인 필요 영역 구분, 테스트 플로우, 실패 연락처)

## 후속 작업

- 토스 userKey ↔ Supabase 사용자 매핑 (결제/구독 연동 시 필요)
- 앱인토스 IAP 구독 결제 (팩트콕 `tossIapClient.ts` 패턴 재사용)
- 심사용 리뷰 노트 작성 및 제출
