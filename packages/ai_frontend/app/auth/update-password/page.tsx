'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import Link from 'next/link'
import { ArrowLeftIcon, SparklesIcon, KeyIcon } from '@heroicons/react/24/outline'

export default function UpdatePasswordPage() {
  const router = useRouter()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)

    if (password.length < 6) {
      setError('비밀번호는 최소 6자 이상이어야 합니다.')
      setLoading(false)
      return
    }

    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.')
      setLoading(false)
      return
    }

    try {
      const supabase = createClient()
      const { error } = await supabase.auth.updateUser({
        password: password,
      })

      if (error) {
        throw error
      }

      setMessage('비밀번호가 성공적으로 변경되었습니다. 로그인 페이지로 이동합니다...')
      
      setTimeout(() => {
        router.push('/auth/login')
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '비밀번호 변경에 실패했습니다.')
    } finally {
      setLoading(false)
    }
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

          <div className="material-auth__form">
            <div className="material-auth__header">
              <div className="material-auth__icon-wrapper">
                <KeyIcon className="material-auth__icon" aria-hidden="true" />
              </div>
              <h2 className="material-auth__title">새 비밀번호 설정</h2>
              <p className="material-auth__description">
                새로운 비밀번호를 입력해주세요.
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
                  onChange={(e) => setPassword(e.target.value)}
                  className="material-form__input"
                  placeholder="최소 6자"
                />
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
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="material-form__input"
                  placeholder="비밀번호 재입력"
                />
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
        </div>

        <div className="material-auth__visual">
          <div className="material-auth__pattern"></div>
        </div>
      </div>
    </div>
  )
}
