# 🚀 빠른 시작 가이드

현재 Supabase 환경 변수가 설정되지 않아 인증 시스템이 비활성화되어 있습니다.

## ⚠️ 현재 상태

```
❌ KIM_BYUN_SUPABASE_URL: 미설정
❌ KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY: 미설정
```

인증 기능을 사용하려면 아래 단계를 따라주세요.

## 📝 설정 단계 (5분 소요)

### 1단계: Supabase 프로젝트 생성

1. https://supabase.com/dashboard 접속
2. "New Project" 클릭
3. 프로젝트 이름, 데이터베이스 비밀번호, 리전 선택
4. "Create new project" 클릭 (약 2분 소요)

### 2단계: API 키 가져오기

프로젝트 생성 완료 후:

1. 왼쪽 메뉴에서 **Settings** (⚙️) 클릭
2. **API** 클릭
3. 다음 두 값을 복사:
   - **Project URL** (예: `https://xxxxx.supabase.co`)
   - **anon public** key (긴 문자열)

### 3단계: 환경 변수 설정

`.env.local` 파일을 열고 다음 값을 **실제 값으로 교체**하세요:

```bash
# 현재 (❌ 잘못된 값)
KIM_BYUN_SUPABASE_URL=your-project-url-here
KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here

# 변경 후 (✅ 실제 값)
KIM_BYUN_SUPABASE_URL=https://xxxxx.supabase.co
KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...실제키...
```

### 4단계: Email Provider 활성화

Supabase Dashboard에서:

1. **Authentication** 메뉴 클릭
2. **Providers** 탭 클릭
3. **Email** 활성화 (기본적으로 활성화되어 있을 수 있음)
4. "Confirm email" 옵션 설정 (선택사항)

### 5단계: Redirect URLs 설정

1. **Authentication** > **URL Configuration** 클릭
2. **Site URL** 확인: `http://localhost:3000`
3. **Redirect URLs** 섹션에서 "Add URL" 클릭, 다음 추가:
   ```
   http://localhost:3000/api/auth/callback
   http://localhost:3000/auth/callback
   ```

### 6단계: 개발 서버 재시작

```bash
# 현재 실행 중인 서버 중지 (Ctrl+C)
# 그리고 다시 시작:
npm run dev
```

## ✅ 확인하기

설정이 완료되었는지 확인:

```bash
./check-supabase.sh
```

## 🧪 테스트

브라우저에서 다음 페이지 접속:

1. **회원가입**: http://localhost:3000/auth/signup
2. **로그인**: http://localhost:3000/auth/login
3. **데모**: http://localhost:3000/demo (로그인 후)

## 🎯 첫 사용자 생성

1. http://localhost:3000/auth/signup 접속
2. 이메일과 비밀번호 입력
3. "회원가입" 클릭
4. **이메일 확인** (개발 중에는 Supabase Dashboard에서 확인 가능)
   - Dashboard > Authentication > Users에서 확인
   - 이메일 확인 링크 클릭하거나 Dashboard에서 수동 확인

## 📧 이메일 확인 (개발 중)

개발 환경에서는 이메일이 실제로 전송되지 않을 수 있습니다.

**방법 1: Dashboard에서 수동 확인**
1. Supabase Dashboard > Authentication > Users
2. 사용자 클릭
3. "Email Confirmed" 체크박스 활성화

**방법 2: 확인 링크 복사**
1. Dashboard > Authentication > Users
2. 사용자의 "Confirmation Link" 복사
3. 브라우저에서 열기

## 🐛 문제 해결

### "Invalid API key" 오류

```bash
# 환경 변수 확인
cat .env.local | grep SUPABASE

# 서버 재시작
npm run dev
```

### 이메일이 전송되지 않음

- 개발 중에는 Dashboard에서 수동 확인 사용
- 프로덕션: SMTP 설정 필요 (Settings > Auth > SMTP Settings)

### 로그인이 안됨

1. 이메일이 확인되었는지 Dashboard에서 확인
2. 비밀번호가 최소 6자인지 확인
3. 브라우저 콘솔에서 에러 메시지 확인

## 🔒 Supabase 설정 체크리스트

- [ ] Supabase 프로젝트 생성됨
- [ ] `.env.local`에 실제 URL과 KEY 설정됨
- [ ] Email Provider 활성화됨
- [ ] Redirect URLs 추가됨 (2개)
- [ ] 개발 서버 재시작됨
- [ ] http://localhost:3000/auth/signup 접속 가능
- [ ] 첫 사용자 생성 및 확인 완료

## 📚 더 알아보기

- **전체 가이드**: `AUTH_README.md`
- **아키텍처**: `ARCHITECTURE.md`
- **마이그레이션**: `MIGRATION_GUIDE.md`
- **공식 문서**: https://supabase.com/docs/guides/auth

## 🎉 완료!

모든 단계를 완료하면 다음과 같이 표시됩니다:

```
✅ Supabase 환경 변수가 설정되어 있습니다!
```

이제 인증 시스템을 사용할 수 있습니다!

---

**💡 팁**: 설정 중 문제가 있으면 `./check-supabase.sh`를 실행하여 현재 상태를 확인하세요.
