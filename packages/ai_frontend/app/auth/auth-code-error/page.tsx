import Link from 'next/link'
import { ExclamationTriangleIcon, SparklesIcon, ArrowLeftIcon } from '@heroicons/react/24/outline'

export default function AuthCodeErrorPage() {
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

          <div className="material-auth__error-state">
            <div className="material-auth__error-icon">
              <ExclamationTriangleIcon className="material-icon" aria-hidden="true" />
            </div>
            
            <h2 className="material-auth__error-title">인증 오류</h2>
            <p className="material-auth__error-description">
              인증 코드가 유효하지 않거나 만료되었습니다.
            </p>

            <div className="material-alert material-alert--error">
              이메일 링크가 만료되었거나 이미 사용되었을 수 있습니다.
              다시 시도해주세요.
            </div>

            <div className="material-auth__error-actions">
              <Link href="/auth/login" className="material-filled-button">
                <span>로그인으로 이동</span>
              </Link>
              <Link href="/auth/reset-password" className="material-text-button">
                <span>비밀번호 재설정 다시 요청</span>
              </Link>
            </div>
          </div>
        </div>

        <div className="material-auth__visual">
          <div className="material-auth__pattern"></div>
        </div>
      </div>
    </div>
  )
}
