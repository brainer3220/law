import Link from 'next/link'

export default function AuthCodeErrorPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6 text-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-gray-900">
            인증 오류
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            인증 코드가 유효하지 않거나 만료되었습니다.
          </p>
        </div>

        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-800">
            이메일 링크가 만료되었거나 이미 사용되었을 수 있습니다.
            다시 시도해주세요.
          </p>
        </div>

        <div className="flex flex-col space-y-2">
          <Link
            href="/auth/login"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
          >
            로그인으로 이동
          </Link>
          <Link
            href="/auth/reset-password"
            className="text-sm text-blue-600 hover:text-blue-500"
          >
            비밀번호 재설정 다시 요청
          </Link>
        </div>
      </div>
    </div>
  )
}
