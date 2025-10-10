'use client'

/**
 * Workspace 메인 페이지
 * 프로젝트 타임라인 뷰
 */

import { useState } from 'react'
import { useAuth } from '@/lib/auth/AuthContext'
import ProjectTimeline from '@/components/workspace/ProjectTimeline'
import CreateProjectModal from '@/components/workspace/CreateProjectModal'
import { PlusIcon } from '@heroicons/react/24/outline'

export default function WorkspacePage() {
  const { user, loading } = useAuth()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleProjectCreated = () => {
    // Trigger timeline refresh
    setRefreshKey((prev) => prev + 1)
  }

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

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            로그인이 필요합니다
          </h2>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            프로젝트를 보려면 먼저 로그인하세요.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-200 dark:bg-slate-900/80 dark:border-gray-800">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                프로젝트
              </h1>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                프로젝트 중심 컨텍스트 관리
              </p>
            </div>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              <PlusIcon className="h-5 w-5" />
              <span>새 프로젝트</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
          {/* Status header - similar to screenshot */}
          <div className="border-b border-gray-200 dark:border-gray-800 px-6 py-3 bg-gray-50 dark:bg-slate-900/50">
            <button className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
              <span className="inline-block h-2 w-2 rounded-full bg-green-500"></span>
              <span>On track</span>
            </button>
          </div>

          {/* Project timeline */}
          <ProjectTimeline key={refreshKey} />
        </div>

        {/* Info box */}
        <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-200">
            💡 프로젝트 기반 작업
          </h3>
          <p className="mt-1 text-sm text-blue-800 dark:text-blue-300">
            각 프로젝트는 독립적인 컨텍스트를 가지며, 파일, 메모리, 채팅 기록을 관리합니다.
          </p>
        </div>
      </main>

      {/* Create project modal */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </div>
  )
}
