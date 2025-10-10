'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import Link from 'next/link'
import App from "./App"
import SoftrHero from "@/components/SoftrHero"

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

  // If user is not logged in, show Softr hero landing page with auth buttons
  return (
    <main className="min-h-screen bg-white dark:bg-slate-950">
      {/* Header Navigation with Auth Buttons */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200 dark:bg-slate-900/80 dark:border-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo/Brand */}
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                법률 AI 에이전트
              </h1>
            </div>

            {/* Auth Buttons */}
            <div className="flex items-center gap-3">
              <Link
                href="/auth/login"
                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:text-gray-300 dark:hover:bg-slate-800"
              >
                로그인
              </Link>
              <Link
                href="/auth/signup"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                회원가입
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content with padding for fixed header */}
      <div className="pt-16">
        <SoftrHero />
      </div>
    </main>
  )
}
