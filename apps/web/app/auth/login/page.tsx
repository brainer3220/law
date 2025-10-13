import { LoginForm } from '@/components/auth/LoginForm'
import { Suspense } from 'react'
import Link from 'next/link'
import { ArrowLeftIcon, SparklesIcon } from '@heroicons/react/24/outline'

function LoginPageContent() {
  return (
    <div className="material-auth">
      <div className="material-auth__wrapper">
        <div className="material-auth__container">
          <Link href="/" className="material-auth__back">
            <ArrowLeftIcon className="material-icon" aria-hidden="true" />
            <span>홈으로</span>
          </Link>
          
          <div className="material-auth__brand">
            <div className="material-auth__brand-icon">
              <SparklesIcon className="material-icon" aria-hidden="true" />
            </div>
            <h1 className="material-auth__brand-text">법률 AI 에이전트</h1>
          </div>

          <LoginForm />
        </div>

        <div className="material-auth__visual">
          <div className="material-auth__pattern"></div>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="material-screen">
        <div className="material-loading">
          <div className="material-loading__spinner">
            <div className="spinner-ring"></div>
          </div>
          <p className="material-body">로딩 중...</p>
        </div>
      </div>
    }>
      <LoginPageContent />
    </Suspense>
  )
}
