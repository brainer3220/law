import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json()

    if (!email || !password) {
      return NextResponse.json(
        { error: '이메일과 비밀번호를 입력해주세요.' },
        { status: 400 }
      )
    }

    const supabase = await createClient()

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      console.error('Login error from Supabase:', error)
      return NextResponse.json(
        { error: error.message },
        { status: 401 }
      )
    }

    if (!data.session) {
      return NextResponse.json(
        { error: '세션 생성에 실패했습니다.' },
        { status: 500 }
      )
    }

    // Create response with success message
    const response = NextResponse.json(
      { 
        user: data.user,
        message: '로그인 성공'
      },
      { status: 200 }
    )

    // The cookies are automatically set by the supabase client
    // through the server client's cookie handling
    console.log('Login successful for user:', data.user.email)

    return response
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json(
      { error: '로그인 중 오류가 발생했습니다.' },
      { status: 500 }
    )
  }
}
