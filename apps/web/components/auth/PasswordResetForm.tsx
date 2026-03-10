'use client'

import { useState } from 'react'
import Link from 'next/link'
import { KeyIcon } from '@heroicons/react/24/outline'

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export function PasswordResetForm() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setFieldError(null)
    setFormError(null)

    if (!email.trim()) {
      setFieldError('이메일을 입력해주세요.')
      setLoading(false)
      return
    }

    if (!isValidEmail(email)) {
      setFieldError('올바른 이메일 형식을 입력해주세요.')
      setLoading(false)
      return
    }

    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || '비밀번호 재설정 요청에 실패했습니다.')
      }

      setSubmittedEmail(email.trim())
      setEmail('')
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '비밀번호 재설정 요청에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  if (submittedEmail) {
    return (
      <div className="material-auth__form">
        <div className="material-auth__header">
          <div className="material-auth__icon-wrapper">
            <KeyIcon className="material-auth__icon" aria-hidden="true" />
          </div>
          <h2 className="material-auth__title">재설정 메일을 보냈습니다</h2>
          <p className="material-auth__description">
            {submittedEmail} 주소로 비밀번호 재설정 링크를 전송했습니다.
          </p>
        </div>

        <div className="material-form__actions">
          <div className="material-alert material-alert--success" role="status" aria-live="polite">
            메일함과 스팸함을 확인해주세요. 링크를 열면 새 비밀번호를 바로 설정할 수 있습니다.
          </div>
          <Link href="/auth/login" className="material-filled-button material-form__submit">
            <span>로그인으로 돌아가기</span>
          </Link>
          <button
            type="button"
            onClick={() => {
              setSubmittedEmail(null)
              setFieldError(null)
              setFormError(null)
            }}
            className="material-text-button"
          >
            다른 이메일로 다시 요청하기
          </button>
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
        <h2 className="material-auth__title">비밀번호 재설정</h2>
        <p className="material-auth__description">
          가입한 이메일 주소를 입력하면 새 비밀번호를 설정할 수 있는 링크를 보내드립니다.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="material-form" noValidate>
        {formError && (
          <div className="material-alert material-alert--error" role="alert">
            {formError}
          </div>
        )}

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
              setFieldError(null)
              setFormError(null)
            }}
            className="material-form__input"
            placeholder="name@example.com"
            aria-invalid={fieldError ? 'true' : 'false'}
            aria-describedby={fieldError ? 'reset-email-error' : 'reset-email-help'}
          />
          <p id="reset-email-help" className="material-form__support">
            메일이 도착하지 않으면 스팸함을 확인하고, 몇 분 뒤 다시 시도해주세요.
          </p>
          {fieldError && (
            <p id="reset-email-error" className="material-form__support material-form__support--error">
              {fieldError}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="material-filled-button material-form__submit"
        >
          <span>{loading ? '전송 중...' : '재설정 링크 전송'}</span>
        </button>

        <div className="material-form__helper">
          <Link href="/auth/login" className="material-link">
            로그인으로 돌아가기
          </Link>
        </div>
      </form>
    </div>
  )
}
