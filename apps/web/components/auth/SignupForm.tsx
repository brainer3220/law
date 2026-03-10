'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { UserPlusIcon } from '@heroicons/react/24/outline'

interface FieldErrors {
  fullName?: string
  email?: string
  password?: string
  confirmPassword?: string
}

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export function SignupForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  const passwordHint = useMemo(
    () => '비밀번호는 최소 6자 이상이어야 하며, 확인 입력과 일치해야 합니다.',
    []
  )

  const validateForm = () => {
    const nextErrors: FieldErrors = {}

    if (!fullName.trim()) {
      nextErrors.fullName = '이름을 입력해주세요.'
    }

    if (!email.trim()) {
      nextErrors.email = '이메일을 입력해주세요.'
    } else if (!isValidEmail(email)) {
      nextErrors.email = '올바른 이메일 형식을 입력해주세요.'
    }

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

  const resetForm = () => {
    setSubmittedEmail(null)
    setFormError(null)
    setFieldErrors({})
    setPassword('')
    setConfirmPassword('')
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
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim(),
          password,
          fullName: fullName.trim(),
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || '회원가입에 실패했습니다.')
      }

      setSubmittedEmail(email.trim())
      setPassword('')
      setConfirmPassword('')
      setFieldErrors({})
      setFormError(null)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '회원가입에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (submittedEmail) {
    return (
      <div className="material-auth__form">
        <div className="material-auth__header">
          <div className="material-auth__icon-wrapper">
            <UserPlusIcon className="material-auth__icon" aria-hidden="true" />
          </div>
          <h2 className="material-auth__title">인증 메일을 보냈습니다</h2>
          <p className="material-auth__description">
            {submittedEmail} 주소로 계정 확인 링크를 전송했습니다.
          </p>
        </div>

        <div className="material-form__actions">
          <div className="material-alert material-alert--success" role="status" aria-live="polite">
            메일함과 스팸함을 확인한 뒤 인증을 완료해주세요. 인증이 끝나면 로그인 화면에서 바로 접속할 수 있습니다.
          </div>
          <Link href="/auth/login" className="material-filled-button material-form__submit">
            <span>인증 후 로그인</span>
          </Link>
          <button type="button" onClick={resetForm} className="material-text-button">
            다른 이메일로 다시 가입하기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="material-auth__form">
      <div className="material-auth__header">
        <div className="material-auth__icon-wrapper">
          <UserPlusIcon className="material-auth__icon" aria-hidden="true" />
        </div>
        <h2 className="material-auth__title">회원가입</h2>
        <p className="material-auth__description">
          이미 계정이 있으신가요?{' '}
          <Link href="/auth/login" className="material-link">
            로그인
          </Link>
        </p>
      </div>

      <form onSubmit={handleSubmit} className="material-form" noValidate>
        {formError && (
          <div className="material-alert material-alert--error" role="alert">
            {formError}
          </div>
        )}

        <div className="material-form__field">
          <label htmlFor="fullName" className="material-form__label">
            이름
          </label>
          <input
            id="fullName"
            name="fullName"
            type="text"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value)
              setFieldErrors((prev) => ({ ...prev, fullName: undefined }))
              setFormError(null)
            }}
            className="material-form__input"
            placeholder="홍길동"
            aria-invalid={fieldErrors.fullName ? 'true' : 'false'}
            aria-describedby={fieldErrors.fullName ? 'signup-fullname-error' : undefined}
          />
          {fieldErrors.fullName && (
            <p id="signup-fullname-error" className="material-form__support material-form__support--error">
              {fieldErrors.fullName}
            </p>
          )}
        </div>

        <div className="material-form__field">
          <label htmlFor="email" className="material-form__label">
            이메일
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              setFieldErrors((prev) => ({ ...prev, email: undefined }))
              setFormError(null)
            }}
            className="material-form__input"
            placeholder="name@example.com"
            aria-invalid={fieldErrors.email ? 'true' : 'false'}
            aria-describedby={fieldErrors.email ? 'signup-email-error' : undefined}
          />
          {fieldErrors.email && (
            <p id="signup-email-error" className="material-form__support material-form__support--error">
              {fieldErrors.email}
            </p>
          )}
        </div>

        <div className="material-form__field">
          <label htmlFor="password" className="material-form__label">
            비밀번호
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
            aria-describedby={fieldErrors.password ? 'signup-password-error' : 'signup-password-hint'}
          />
          <p id="signup-password-hint" className="material-form__support">
            {passwordHint}
          </p>
          {fieldErrors.password && (
            <p id="signup-password-error" className="material-form__support material-form__support--error">
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
            aria-describedby={fieldErrors.confirmPassword ? 'signup-confirm-password-error' : undefined}
          />
          {fieldErrors.confirmPassword && (
            <p
              id="signup-confirm-password-error"
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
          <span>{loading ? '가입 중...' : '회원가입'}</span>
        </button>
      </form>
    </div>
  )
}
