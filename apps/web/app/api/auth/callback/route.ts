import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'
import { NextRequest } from 'next/server'

function getSafeNextPath(next: string | null) {
  if (!next || !next.startsWith('/')) {
    return '/auth/login?verified=1'
  }

  return next
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  const next = getSafeNextPath(searchParams.get('next'))
  let errorMessage: string | null = null

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    
    if (!error) {
      return NextResponse.redirect(new URL(next, request.url))
    }

    errorMessage = error.message
  }

  // Return the user to an error page with instructions
  const errorUrl = new URL('/auth/auth-code-error', request.url)
  errorUrl.searchParams.set('reason', 'verification')

  if (errorMessage) {
    errorUrl.searchParams.set('details', errorMessage)
  }

  return NextResponse.redirect(errorUrl)
}
