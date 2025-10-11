'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'

interface LoginFormProps {
  redirectTo?: string
}

export function LoginForm({ redirectTo = '/' }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        credentials: 'same-origin',
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || '로그인에 실패했습니다.')
      }

      setMessage('로그인 성공! 리다이렉트 중...')
      
      await new Promise(resolve => setTimeout(resolve, 500))
      window.location.href = redirectTo
    } catch (err) {
      setError(err instanceof Error ? err.message : '로그인에 실패했습니다.')
      setLoading(false)
    }
  }

  return (
    <div className="material-auth__form">
      <div className="material-auth__header">
        <div className="material-auth__icon-wrapper">
          <ArrowRightOnRectangleIcon className="material-auth__icon" aria-hidden="true" />
        </div>
        <h2 className="material-auth__title">로그인</h2>
        <p className="material-auth__description">
          계정이 없으신가요?{' '}
          <Link href="/auth/signup" className="material-link">
            회원가입
          </Link>
        </p>
      </div>

      <form onSubmit={handleSubmit} className="material-form">
        {error && (
          <div className="material-alert material-alert--error">
            {error}
          </div>
        )}

        {message && (
          <div className="material-alert material-alert--success">
            {message}
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
            onChange={(e) => setEmail(e.target.value)}
            className="material-form__input"
            placeholder="your@email.com"
          />
        </div>

        <div className="material-form__field">
          <label htmlFor="password" className="material-form__label">
            비밀번호
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="material-form__input"
            placeholder="••••••••"
          />
        </div>

        <div className="material-form__helper">
          <Link href="/auth/reset-password" className="material-link">
            비밀번호를 잊으셨나요?
          </Link>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="material-filled-button material-form__submit"
        >
          <span>{loading ? '로그인 중...' : '로그인'}</span>
        </button>
      </form>
    </div>
  )
}
