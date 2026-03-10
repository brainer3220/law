'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { useAuth } from '@/lib/auth/AuthContext'
import {
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  KeyIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'

interface FieldErrors {
  password?: string
  confirmPassword?: string
}

type LinkState = 'checking' | 'ready' | 'invalid'

export default function UpdatePasswordPage() {
  const { user, loading: authLoading } = useAuth()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isComplete, setIsComplete] = useState(false)
  const [linkState, setLinkState] = useState<LinkState>('checking')
  const [linkError, setLinkError] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) {
      return
    }

    let cancelled = false

    let supabase: ReturnType<typeof createClient>

    try {
      supabase = createClient()
    } catch (error) {
      console.error('Failed to initialize Supabase client:', error)
      setLinkState('invalid')
      setLinkError('인증 설정을 확인할 수 없습니다. 잠시 후 다시 시도해주세요.')
      return
    }

    const currentUrl = new URL(window.location.href)
    const hashParams = new URLSearchParams(currentUrl.hash.replace(/^#/, ''))
    const authError =
      currentUrl.searchParams.get('error_description') ??
      hashParams.get('error_description') ??
      currentUrl.searchParams.get('error') ??
      hashParams.get('error')
    const hasRecoveryParams =
      currentUrl.searchParams.get('type') === 'recovery' ||
      hashParams.get('type') === 'recovery' ||
      hashParams.has('access_token') ||
      hashParams.has('refresh_token') ||
      currentUrl.searchParams.has('code')

    if (authError) {
      setLinkState('invalid')
      setLinkError(authError)
      return
    }

    if (user) {
      setLinkState('ready')
      setLinkError(null)
      return
    }

    if (!hasRecoveryParams) {
      setLinkState('invalid')
      setLinkError('유효한 비밀번호 재설정 링크가 없습니다. 메일에서 받은 링크로 다시 접속해주세요.')
      return
    }

    const markReady = () => {
      if (cancelled) {
        return
      }

      window.clearTimeout(fallbackTimer)

      setLinkState('ready')
      setLinkError(null)
    }

    const markInvalid = () => {
      if (cancelled) {
        return
      }

      setLinkState('invalid')
      setLinkError('비밀번호 재설정 링크가 유효하지 않거나 만료되었습니다. 다시 요청해주세요.')
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'PASSWORD_RECOVERY' || session?.user) {
        markReady()
      }
    })

    void supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        markReady()
      }
    })

    const fallbackTimer = window.setTimeout(async () => {
      const { data: { session } } = await supabase.auth.getSession()

      if (session?.user) {
        markReady()
        return
      }

      markInvalid()
    }, 1200)

    return () => {
      cancelled = true
      subscription.unsubscribe()
      window.clearTimeout(fallbackTimer)
    }
  }, [authLoading, user])

  const validateForm = () => {
    const nextErrors: FieldErrors = {}

    if (password.length < 6) {
      nextErrors.password = '비밀번호는 최소 6자 이상이어야 합니다.'
    }

    if (!confirmPassword) {
      nextErrors.confirmPassword = '비밀번호 확인을 입력해주세요.'
    } else if (password !== confirmPassword) {
      nextErrors.confirmPassword = '비밀번호가 일치하지 않습니다.'
    }

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setFormError(null)

    if (!validateForm()) {
      setLoading(false)
      return
    }

    try {
      const supabase = createClient()
      const { error } = await supabase.auth.updateUser({ password })

      if (error) {
        throw error
      }

      await supabase.auth.signOut()
      setPassword('')
      setConfirmPassword('')
      setFieldErrors({})
      setIsComplete(true)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '비밀번호 변경에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const renderContent = () => {
    if (authLoading || linkState === 'checking') {
      return (
        <div className="material-auth__form">
          <div className="material-auth__header">
            <div className="material-auth__icon-wrapper">
              <KeyIcon className="material-auth__icon" aria-hidden="true" />
            </div>
            <h2 className="material-auth__title">링크 확인 중</h2>
            <p className="material-auth__description">
              비밀번호 재설정 링크와 세션 상태를 확인하고 있습니다.
            </p>
          </div>

          <div className="material-alert material-alert--success" role="status" aria-live="polite">
            잠시만 기다려주세요.
          </div>
        </div>
      )
    }

    if (linkState === 'invalid') {
      return (
        <div className="material-auth__error-state">
          <div className="material-auth__error-icon">
            <ExclamationTriangleIcon className="material-icon" aria-hidden="true" />
          </div>
          <h2 className="material-auth__error-title">링크를 사용할 수 없습니다</h2>
          <p className="material-auth__error-description">
            {linkError ?? '비밀번호 재설정 링크가 유효하지 않거나 만료되었습니다.'}
          </p>
          <div className="material-alert material-alert--error" role="alert">
            새 재설정 메일을 요청한 뒤 가장 최근에 받은 링크를 다시 열어주세요.
          </div>
          <div className="material-auth__actions">
            <Link href="/auth/reset-password" className="material-filled-button">
              <span>재설정 링크 다시 요청</span>
            </Link>
            <Link href="/auth/login" className="material-text-button">
              <span>로그인으로 돌아가기</span>
            </Link>
          </div>
        </div>
      )
    }

    if (isComplete) {
      return (
        <div className="material-auth__form">
          <div className="material-auth__header">
            <div className="material-auth__icon-wrapper">
              <KeyIcon className="material-auth__icon" aria-hidden="true" />
            </div>
            <h2 className="material-auth__title">비밀번호가 변경되었습니다</h2>
            <p className="material-auth__description">
              새 비밀번호로 다시 로그인해 계속 진행해주세요.
            </p>
          </div>

          <div className="material-form__actions">
            <div className="material-alert material-alert--success" role="status" aria-live="polite">
              보안을 위해 현재 복구 세션을 종료했습니다.
            </div>
            <Link href="/auth/login?reset=success" className="material-filled-button material-form__submit">
              <span>로그인하러 가기</span>
            </Link>
          </div>
        </div>
      )
    }

    return (
      <div className="material-auth__form">
        <div className="material-auth__header">
          <div className="material-auth__icon-wrapper">
            <KeyIcon className="material-auth__icon" aria-hidden="true" />
          </div>
          <h2 className="material-auth__title">새 비밀번호 설정</h2>
          <p className="material-auth__description">
            새로운 비밀번호를 입력해주세요. 설정이 끝나면 다시 로그인할 수 있습니다.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="material-form" noValidate>
          {formError && (
            <div className="material-alert material-alert--error" role="alert">
              {formError}
            </div>
          )}

          <div className="material-form__field">
            <label htmlFor="password" className="material-form__label">
              새 비밀번호
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                setFieldErrors((prev) => ({
                  ...prev,
                  password: undefined,
                  confirmPassword: undefined,
                }))
                setFormError(null)
              }}
              className="material-form__input"
              placeholder="최소 6자"
              aria-invalid={fieldErrors.password ? 'true' : 'false'}
              aria-describedby={fieldErrors.password ? 'update-password-error' : 'update-password-help'}
            />
            <p id="update-password-help" className="material-form__support">
              기존과 다른 비밀번호를 설정하면 보안에 더 도움이 됩니다.
            </p>
            {fieldErrors.password && (
              <p id="update-password-error" className="material-form__support material-form__support--error">
                {fieldErrors.password}
              </p>
            )}
          </div>

          <div className="material-form__field">
            <label htmlFor="confirmPassword" className="material-form__label">
              비밀번호 확인
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value)
                setFieldErrors((prev) => ({ ...prev, confirmPassword: undefined }))
                setFormError(null)
              }}
              className="material-form__input"
              placeholder="비밀번호 재입력"
              aria-invalid={fieldErrors.confirmPassword ? 'true' : 'false'}
              aria-describedby={fieldErrors.confirmPassword ? 'update-confirm-password-error' : undefined}
            />
            {fieldErrors.confirmPassword && (
              <p
                id="update-confirm-password-error"
                className="material-form__support material-form__support--error"
              >
                {fieldErrors.confirmPassword}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="material-filled-button material-form__submit"
          >
            <span>{loading ? '변경 중...' : '비밀번호 변경'}</span>
          </button>
        </form>
      </div>
    )
  }

  return (
    <div className="material-auth">
      <div className="material-auth__wrapper">
        <div className="material-auth__container">
          <Link href="/auth/login" className="material-auth__back">
            <ArrowLeftIcon className="material-icon" aria-hidden="true" />
            <span>로그인으로</span>
          </Link>

          <div className="material-auth__brand">
            <div className="material-auth__brand-icon">
              <SparklesIcon className="material-icon" aria-hidden="true" />
            </div>
            <h1 className="material-auth__brand-text">법률 AI 에이전트</h1>
          </div>

          {renderContent()}
        </div>

        <div className="material-auth__visual">
          <div className="material-auth__pattern"></div>
        </div>
      </div>
    </div>
  )
}
