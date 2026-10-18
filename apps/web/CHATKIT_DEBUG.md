# ChatKit 로딩 문제 디버깅 가이드

## 🔍 문제 진단 단계

### 1단계: 터미널에서 서버 로그 확인

개발 서버를 실행하고 로그를 확인하세요:

```bash
npm run dev
```

로그인 후 루트 페이지(`/`)로 이동했을 때 다음과 같은 로그가 나와야 합니다:

```
✅ 정상 작동 시:
[create-session] Resolving user ID...
[create-session] Attempting to get Supabase user...
[create-session] Supabase user result: { userId: 'xxx-xxx-xxx', error: null }
[create-session] Using Supabase user ID: xxx-xxx-xxx
[create-session] Workflow ID: wf_68e4953ec36c81908554d777a725196a...
[create-session] handling request { ... }
[create-session] upstream response { status: 200, statusText: 'OK' }
```

```
❌ 문제 발생 시 가능한 로그:
[create-session] Missing OPENAI_API_KEY
[create-session] Missing workflow ID
[create-session] Error getting Supabase user: ...
[create-session] upstream response { status: 401, statusText: 'Unauthorized' }
```

### 2단계: 브라우저 개발자 도구 확인

1. **브라우저에서 F12 또는 Cmd+Option+I**
2. **Network 탭 열기**
3. 페이지 새로고침
4. `create-session` 요청 찾기

#### 확인 사항:

- **요청이 전송되는가?**
  - ❌ 안되면: ChatKit 컴포넌트가 마운트되지 않았거나 에러 발생
  
- **응답 Status Code는?**
  - ✅ 200: 정상
  - ❌ 400: Workflow ID 누락
  - ❌ 401: OpenAI API Key 문제
  - ❌ 500: 서버 에러

- **응답 Body는?**
  ```json
  {
    "id": "sess_xxx",
    "workflow": { "id": "wf_xxx" },
    "user": "user-id"
  }
  ```

### 3단계: Console 탭에서 에러 확인

```javascript
// 정상 작동 시
✅ No errors

// 문제 발생 시
❌ Failed to load resource: the server responded with a status of 500
❌ Unhandled Runtime Error
❌ TypeError: Cannot read property 'id' of undefined
```

## 🐛 일반적인 문제와 해결책

### 문제 1: "Missing OPENAI_API_KEY"

**증상:**
```
[create-session] Missing OPENAI_API_KEY
```

**해결:**
1. `.env.local` 파일 확인
2. `OPENAI_API_KEY=sk-proj-...` 설정되어 있는지 확인
3. 개발 서버 재시작: `npm run dev`

### 문제 2: "Missing workflow id"

**증상:**
```
[create-session] Missing workflow ID
```

**해결:**
1. `.env.local` 파일 확인
2. `NEXT_PUBLIC_CHATKIT_WORKFLOW_ID=wf_...` 설정되어 있는지 확인
3. 개발 서버 재시작: `npm run dev`

### 문제 3: 401 Unauthorized from OpenAI

**증상:**
```
[create-session] upstream response { status: 401 }
```

**해결:**
1. OpenAI API Key가 유효한지 확인
2. API Key에 ChatKit 베타 접근 권한이 있는지 확인
3. OpenAI Dashboard에서 새 Key 발급

### 문제 4: Supabase 인증 실패

**증상:**
```
[create-session] Error getting Supabase user: ...
```

**해결:**
1. 로그인이 제대로 되었는지 확인
2. 브라우저 쿠키에 `sb-xxx-auth-token` 있는지 확인
3. 로그아웃 후 다시 로그인

### 문제 5: CORS 에러

**증상:**
```
Access to fetch at 'xxx' has been blocked by CORS policy
```

**해결:**
1. Next.js가 `localhost:3000`에서 실행되는지 확인
2. 다른 포트나 도메인 사용 시 `next.config.js` 설정 필요

## 🔧 강제 디버깅 모드

더 자세한 로그를 보려면:

### 1. ChatKitPanel 컴포넌트 확인

`components/ChatKitPanel.tsx`에서:

```tsx
useEffect(() => {
  console.log('ChatKitPanel mounted');
  console.log('Theme:', theme);
  console.log('Workflow ID from config:', WORKFLOW_ID);
}, []);
```

### 2. API 직접 테스트

터미널에서:

```bash
curl -X POST http://localhost:3000/api/create-session \
  -H "Content-Type: application/json" \
  -H "Cookie: sb-xxx-auth-token=..." \
  -d '{"workflow":{"id":"wf_68e4953ec36c81908554d777a725196a0e7b93607f1d9339"}}'
```

## 📝 체크리스트

로딩 문제 해결 전에 확인:

- [ ] 개발 서버가 실행 중 (`npm run dev`)
- [ ] `.env.local`에 모든 환경 변수 설정됨
- [ ] 로그인이 정상적으로 완료됨
- [ ] 브라우저 쿠키에 Supabase 토큰 존재
- [ ] 터미널에서 `[create-session]` 로그 확인
- [ ] 브라우저 Network 탭에서 요청/응답 확인
- [ ] Console 탭에서 에러 메시지 확인

## 🆘 여전히 안될 때

다음 정보를 수집하세요:

1. **터미널 로그** (모든 `[create-session]` 메시지)
2. **Network 탭 스크린샷** (`create-session` 요청)
3. **Console 탭 에러 메시지**
4. **환경 변수 설정** (민감 정보 제외)

---

**💡 팁:** 대부분의 경우 개발 서버 재시작만으로 해결됩니다!

```bash
# Ctrl+C로 서버 중지
npm run dev
```

## 📮 OpenAI 지원 요청 시 x-request-id 수집 (BRA-13)

OpenAI 지원팀은 ChatKit API 실패 원인 파악을 위해 `x-request-id` 응답 헤더를 요구합니다.
이제 `create-session` 라우트가 업스트림 실패 시 해당 헤더를 자동으로 수집합니다.

- 서버 로그: `OpenAI ChatKit session creation failed` 항목의 `requestId` 필드
- 클라이언트 응답: 에러 응답 JSON의 `request_id` 필드
- 브라우저 Network 탭: 실패한 `create-session` 또는 `chatkit` 요청의 응답 헤더에서 직접 확인 가능

지원 요청 시 워크플로 ID와 함께 이 값을 전달하세요.
