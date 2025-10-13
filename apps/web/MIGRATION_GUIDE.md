# 기존 페이지에 인증 추가하기

이 가이드는 기존 페이지에 Supabase 인증을 추가하는 방법을 설명합니다.

## 1. Client Component에 인증 추가

### Before (인증 없음)

```tsx
'use client'

export default function MyPage() {
  return <div>내용</div>
}
```

### After (인증 추가)

```tsx
'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

export default function MyPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login')
    }
  }, [user, loading, router])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return null
  }

  return (
    <div>
      <p>Welcome {user.email}</p>
      {/* 기존 내용 */}
    </div>
  )
}
```

## 2. Server Component에 인증 추가

### Before (인증 없음)

```tsx
export default function MyServerPage() {
  return <div>내용</div>
}
```

### After (인증 추가)

```tsx
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function MyServerPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <div>
      <p>Welcome {user.email}</p>
      {/* 기존 내용 */}
    </div>
  )
}
```

## 3. API Route에 인증 추가

### Before (인증 없음)

```tsx
import { NextResponse } from 'next/server'

export async function GET() {
  const data = await fetchData()
  return NextResponse.json({ data })
}
```

### After (인증 추가)

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

  // user.id를 사용하여 사용자별 데이터 필터링
  const data = await fetchData(user.id)
  return NextResponse.json({ data })
}
```

## 4. 네비게이션에 사용자 메뉴 추가

```tsx
import { UserMenu } from '@/components/auth/UserMenu'

export default function Navigation() {
  return (
    <nav className="flex items-center justify-between p-4">
      <div>Logo</div>
      <UserMenu />
    </nav>
  )
}
```

## 5. 조건부 렌더링 (로그인/로그아웃 상태)

```tsx
'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import Link from 'next/link'

export default function HomePage() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      {user ? (
        <div>
          <p>Welcome back, {user.email}!</p>
          <Link href="/demo">Go to Demo</Link>
        </div>
      ) : (
        <div>
          <p>Please sign in to continue</p>
          <Link href="/auth/login">Login</Link>
          <Link href="/auth/signup">Sign Up</Link>
        </div>
      )}
    </div>
  )
}
```

## 6. 사용자 ID로 데이터 필터링 예시

### Supabase Database Query

```tsx
import { createClient } from '@/lib/supabase/server'

export async function getUserDocuments() {
  const supabase = await createClient()
  
  // Get current user
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return { data: null, error: 'Not authenticated' }
  }

  // Query user's documents (RLS 정책이 설정되어 있다면 자동으로 필터링됨)
  const { data, error } = await supabase
    .from('documents')
    .select('*')
    .eq('user_id', user.id)

  return { data, error }
}
```

## 7. Form에서 사용자 정보 자동 입력

```tsx
'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import { useEffect, useState } from 'react'

export default function UserForm() {
  const { user } = useAuth()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')

  useEffect(() => {
    if (user) {
      setEmail(user.email || '')
      setName(user.user_metadata?.full_name || '')
    }
  }, [user])

  return (
    <form>
      <input 
        type="email" 
        value={email} 
        onChange={(e) => setEmail(e.target.value)}
        disabled={!!user} // 이미 로그인된 경우 수정 불가
      />
      <input 
        type="text" 
        value={name} 
        onChange={(e) => setName(e.target.value)}
      />
    </form>
  )
}
```

## 8. 역할 기반 접근 제어 (선택사항)

Supabase에서 사용자 메타데이터에 역할을 저장하고 사용할 수 있습니다.

```tsx
import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // 사용자 역할 확인
  const role = user.user_metadata?.role

  if (role !== 'admin') {
    redirect('/unauthorized')
  }

  return <div>Admin Content</div>
}
```

## 9. 로딩 상태 처리

```tsx
'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function MyPage() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p>Please log in</p>
      </div>
    )
  }

  return <div>Content</div>
}
```

## 10. 에러 처리

```tsx
'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import { useState } from 'react'

export default function MyComponent() {
  const { user, signOut } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleAction = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/protected-action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })

      if (!response.ok) {
        if (response.status === 401) {
          // 인증 만료 - 로그아웃 후 로그인 페이지로
          await signOut()
          throw new Error('세션이 만료되었습니다. 다시 로그인해주세요.')
        }
        throw new Error('작업 실패')
      }

      const data = await response.json()
      // 성공 처리
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
      <button onClick={handleAction} disabled={loading}>
        {loading ? '처리 중...' : '작업 실행'}
      </button>
    </div>
  )
}
```

## 체크리스트

기존 페이지를 보호하기 전에 확인하세요:

- [ ] `.env.local`에 Supabase 환경 변수 설정됨
- [ ] `middleware.ts`가 활성화됨
- [ ] `app/layout.tsx`에 `AuthProvider`가 추가됨
- [ ] 보호할 페이지에 인증 체크 추가됨
- [ ] API 라우트에 인증 확인 추가됨
- [ ] 사용자 메뉴가 네비게이션에 추가됨
- [ ] 로딩 상태와 에러 처리가 구현됨
- [ ] Supabase Row Level Security (RLS) 정책 설정됨 (데이터베이스 사용 시)

## 문제 해결

### "user is null" 문제
- `AuthProvider`가 최상위 레이아웃에 있는지 확인
- 미들웨어가 올바르게 설정되었는지 확인
- 브라우저 콘솔에서 인증 에러 확인

### "Unauthorized" 에러
- 쿠키가 올바르게 설정되는지 확인
- CORS 설정 확인 (다른 도메인 사용 시)
- Supabase 프로젝트의 URL 설정 확인

### 세션이 유지되지 않음
- `middleware.ts`가 모든 요청을 가로채는지 확인
- 쿠키 설정이 올바른지 확인
- 브라우저 개발자 도구에서 쿠키 확인
