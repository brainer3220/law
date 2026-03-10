import Link from 'next/link'
import {
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'

interface PageProps {
  searchParams: Promise<{
    reason?: string
    details?: string
  }>
}

export default async function AuthCodeErrorPage({ searchParams }: PageProps) {
  const { reason, details } = await searchParams

  const content = (() => {
    if (reason === 'verification') {
      return {
        title: '이메일 인증을 완료할 수 없습니다',
        description:
          details ?? '인증 링크가 유효하지 않거나 이미 사용되었습니다. 가입을 다시 진행하거나 로그인 화면으로 이동해주세요.',
        primaryHref: '/auth/signup',
        primaryLabel: '다시 회원가입하기',
        secondaryHref: '/auth/login',
        secondaryLabel: '로그인으로 이동',
        alert: '가장 최근에 받은 인증 메일의 링크를 사용했는지 확인해주세요.',
      }
    }

    if (reason === 'recovery') {
      return {
        title: '복구 링크를 사용할 수 없습니다',
        description:
          details ?? '비밀번호 재설정 링크가 만료되었거나 손상되었습니다. 새 재설정 메일을 요청해주세요.',
        primaryHref: '/auth/reset-password',
        primaryLabel: '재설정 링크 다시 요청',
        secondaryHref: '/auth/login',
        secondaryLabel: '로그인으로 이동',
        alert: '메일함과 스팸함에서 가장 최근에 받은 링크를 다시 확인해보세요.',
      }
    }

    return {
      title: '인증 오류',
      description:
        details ?? '인증 요청을 처리하는 중 문제가 발생했습니다. 다시 시도하거나 로그인 화면으로 이동해주세요.',
      primaryHref: '/auth/login',
      primaryLabel: '로그인으로 이동',
      secondaryHref: '/',
      secondaryLabel: '홈으로',
      alert: '문제가 계속되면 다시 요청한 최신 링크를 사용해주세요.',
    }
  })()

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

            <h2 className="material-auth__error-title">{content.title}</h2>
            <p className="material-auth__error-description">{content.description}</p>

            <div className="material-alert material-alert--error" role="alert">
              {content.alert}
            </div>

            <div className="material-auth__actions">
              <Link href={content.primaryHref} className="material-filled-button">
                <span>{content.primaryLabel}</span>
              </Link>
              <Link href={content.secondaryHref} className="material-text-button">
                <span>{content.secondaryLabel}</span>
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
