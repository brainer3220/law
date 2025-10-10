# Supabase Authentication System

이 프로젝트에는 Supabase를 사용한 완전한 인증 시스템이 구현되어 있습니다.

## 설치 및 설정

### 1. 패키지 설치

이미 설치되어 있지만, 새로 설치하려면:

```bash
npm install @supabase/supabase-js @supabase/ssr
```

### 2. 환경 변수 설정

`.env.local` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# Supabase
KIM_BYUN_SUPABASE_URL=https://your-project.supabase.co
KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Optional: Site URL for email redirects
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

Supabase 프로젝트에서 이 값들을 가져올 수 있습니다:
1. [Supabase Dashboard](https://app.supabase.com) 방문
2. 프로젝트 선택
3. Settings > API 에서 URL과 anon key 복사

### 3. Supabase 프로젝트 설정

Supabase Dashboard에서:

1. **Authentication > Providers**
   - Email 활성화
   - "Confirm email" 옵션 설정 (선택사항)

2. **Authentication > URL Configuration**
   - Site URL: `http://localhost:3000` (개발) 또는 프로덕션 URL
   - Redirect URLs에 추가:
     - `http://localhost:3000/api/auth/callback`
     - `http://localhost:3000/auth/callback`

3. **Authentication > Email Templates**
   - 필요시 이메일 템플릿 커스터마이징

## 구조

```
packages/ai_frontend/
├── lib/
│   ├── auth/
│   │   └── AuthContext.tsx          # React Context for auth state
│   └── supabase/
│       ├── client.ts                # Browser client
│       ├── server.ts                # Server client
│       └── middleware.ts            # Middleware helper
├── components/
│   └── auth/
│       ├── LoginForm.tsx            # 로그인 폼
│       ├── SignupForm.tsx           # 회원가입 폼
│       ├── PasswordResetForm.tsx    # 비밀번호 재설정 폼
│       └── UserMenu.tsx             # 사용자 메뉴 (로그아웃 등)
├── app/
│   ├── api/
│   │   └── auth/
│   │       ├── login/route.ts       # 로그인 API
│   │       ├── signup/route.ts      # 회원가입 API
│   │       ├── logout/route.ts      # 로그아웃 API
│   │       ├── reset-password/route.ts
│   │       ├── callback/route.ts    # OAuth/Email callback
│   │       └── user/route.ts        # 현재 사용자 정보
│   └── auth/
│       ├── login/page.tsx
│       ├── signup/page.tsx
│       ├── reset-password/page.tsx
│       ├── update-password/page.tsx
│       └── auth-code-error/page.tsx
└── middleware.ts                     # Route protection
```

## 사용법

### 페이지에서 인증 상태 확인

```tsx
'use client'

import { useAuth } from '@/lib/auth/AuthContext'

export default function MyPage() {
  const { user, loading, signOut } = useAuth()

  if (loading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return <div>Please log in</div>
  }

  return (
    <div>
      <h1>Welcome {user.email}</h1>
      <button onClick={() => signOut()}>Sign Out</button>
    </div>
  )
}
```

### Server Component에서 사용자 확인

```tsx
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function ProtectedPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <div>
      <h1>Protected Content</h1>
      <p>User: {user.email}</p>
    </div>
  )
}
```

### API Route에서 인증 확인

```tsx
import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET() {
  const supabase = await createClient()
  
  const { data: { user }, error } = await supabase.auth.getUser()

  if (error || !user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }

  // Your protected logic here
  return NextResponse.json({ data: 'Protected data' })
}
```

## 기능

### ✅ 구현된 기능

- [x] 이메일/비밀번호 회원가입
- [x] 이메일/비밀번호 로그인
- [x] 로그아웃
- [x] 비밀번호 재설정 (이메일)
- [x] 이메일 확인
- [x] 세션 관리 (자동 갱신)
- [x] 보호된 라우트 (Middleware)
- [x] 사용자 메뉴 UI
- [x] 에러 처리
- [x] 로딩 상태
- [x] React Context를 통한 전역 상태 관리

### 🔄 확장 가능한 기능

다음 기능들을 쉽게 추가할 수 있습니다:

- OAuth 로그인 (Google, GitHub 등)
- 프로필 업데이트
- 아바타 업로드
- 2단계 인증 (2FA)
- 매직 링크 로그인
- 역할 기반 접근 제어 (RBAC)

## 보호된 라우트

`middleware.ts`는 자동으로 다음을 처리합니다:

1. **인증되지 않은 사용자**
   - `/auth/*` 페이지를 제외한 모든 페이지 접근 시 `/auth/login`으로 리다이렉트

2. **인증된 사용자**
   - `/auth/*` 페이지 접근 시 `/demo`로 리다이렉트

3. **세션 갱신**
   - 모든 요청에서 자동으로 세션 갱신

## 테스트

개발 서버 실행:

```bash
npm run dev
```

테스트할 페이지:
- http://localhost:3000/auth/login - 로그인
- http://localhost:3000/auth/signup - 회원가입
- http://localhost:3000/auth/reset-password - 비밀번호 재설정
- http://localhost:3000/demo - 보호된 데모 페이지

## 문제 해결

### "Invalid API key" 오류

`.env.local` 파일의 환경 변수가 올바른지 확인하세요.

### 이메일이 전송되지 않음

1. Supabase Dashboard > Authentication > Email Templates 확인
2. SMTP 설정 확인 (프로덕션의 경우)
3. 개발 중에는 Supabase Dashboard > Authentication > Users에서 확인 링크 수동 복사 가능

### 세션이 유지되지 않음

1. 쿠키가 제대로 설정되는지 확인
2. Middleware가 올바르게 구성되었는지 확인
3. `KIM_BYUN_SUPABASE_URL`과 `KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY`가 올바른지 확인

## 보안 고려사항

1. **환경 변수**: `.env.local` 파일을 절대 Git에 커밋하지 마세요
2. **HTTPS**: 프로덕션에서는 반드시 HTTPS 사용
3. **Row Level Security**: Supabase에서 RLS 정책 설정
4. **Rate Limiting**: API 엔드포인트에 rate limiting 추가 권장

## 다음 단계

1. Supabase Row Level Security (RLS) 정책 설정
2. 사용자 프로필 테이블 생성
3. OAuth 프로바이더 추가
4. 이메일 템플릿 커스터마이징
5. 사용자 역할 및 권한 시스템 구현

## 참고 자료

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Next.js 15 App Router](https://nextjs.org/docs)
- [Supabase SSR Guide](https://supabase.com/docs/guides/auth/server-side/nextjs)
