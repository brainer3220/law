'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import Link from 'next/link'
import App from "./App"

export default function Home() {
  const { user, loading } = useAuth()

  // Show loading state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  // If user is logged in, show the app
  if (user) {
    return <App />
  }

  // If user is not logged in, show welcome/landing page
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-100 px-6 py-12 dark:bg-slate-950">
      <div className="mx-auto w-full max-w-4xl text-center">
        <div className="mb-8">
          <h1 className="mb-4 text-5xl font-bold text-gray-900 dark:text-white">
            법률 AI 에이전트
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400">
            AI 기반 법률 지원 시스템에 오신 것을 환영합니다
          </p>
        </div>

        <div className="mb-12 grid gap-6 md:grid-cols-3">
          <div className="rounded-lg bg-white p-6 shadow-md dark:bg-slate-900">
            <div className="mb-3 text-4xl">📚</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              법률 검색
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              법령, 판례, 행정규칙을 빠르게 검색하고 분석합니다
            </p>
          </div>

          <div className="rounded-lg bg-white p-6 shadow-md dark:bg-slate-900">
            <div className="mb-3 text-4xl">⚖️</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              사례 분석
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              유사 판례를 찾고 법률적 근거를 제시합니다
            </p>
          </div>

          <div className="rounded-lg bg-white p-6 shadow-md dark:bg-slate-900">
            <div className="mb-3 text-4xl">✍️</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900 dark:text-white">
              문서 작성
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              법률 문서 초안을 AI가 작성해드립니다
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/auth/signup"
              className="rounded-lg bg-blue-600 px-8 py-3 text-center font-semibold text-white shadow-lg hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              회원가입하기
            </Link>
            <Link
              href="/auth/login"
              className="rounded-lg border-2 border-gray-300 bg-white px-8 py-3 text-center font-semibold text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-slate-900 dark:text-gray-300 dark:hover:bg-slate-800"
            >
              로그인
            </Link>
          </div>
          
          <p className="text-sm text-gray-500 dark:text-gray-500">
            이미 계정이 있으신가요?{' '}
            <Link href="/auth/login" className="font-medium text-blue-600 hover:text-blue-500">
              로그인
            </Link>
          </p>
        </div>

        <div className="mt-12 text-sm text-gray-500 dark:text-gray-500">
          <p>💡 서비스를 이용하려면 로그인이 필요합니다</p>
        </div>
      </div>
    </main>
  )
}
