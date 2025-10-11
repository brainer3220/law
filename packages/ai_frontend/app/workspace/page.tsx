'use client'

import '@material/web/button/filled-button.js'
import '@material/web/button/filled-tonal-button.js'
import '@material/web/progress/circular-progress.js'

import { useState } from 'react'
import { useAuth } from '@/lib/auth/AuthContext'
import ProjectTimeline from '@/components/workspace/ProjectTimeline'
import CreateProjectModal from '@/components/workspace/CreateProjectModal'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { CheckCircleIcon, PlusIcon } from '@heroicons/react/24/outline'

export default function WorkspacePage() {
  const { user, loading } = useAuth()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleProjectCreated = () => {
    setRefreshKey((prev) => prev + 1)
  }

  if (loading) {
    return (
      <div className="material-screen">
        <LoadingSpinner label="워크스페이스를 불러오는 중입니다…" />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="material-empty">
        <h2 className="material-title material-empty__title">로그인이 필요합니다</h2>
        <p className="material-body material-empty__body">
          프로젝트를 보려면 먼저 로그인하세요.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="material-workspace">
        <header className="material-workspace__bar">
          <div className="material-workspace__heading">
            <h1 className="material-title">프로젝트</h1>
            <p className="material-caption">프로젝트 중심 컨텍스트 관리</p>
          </div>
          <md-filled-button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
          >
            <PlusIcon slot="icon" className="material-icon" />
            새 프로젝트
          </md-filled-button>
        </header>

        <main className="material-workspace__content">
          <section className="material-workspace__surface">
            <div className="material-workspace__status">
              <CheckCircleIcon className="material-icon" aria-hidden="true" />
              <span className="material-caption">On track</span>
            </div>
            <ProjectTimeline key={refreshKey} />
          </section>

          <aside className="material-workspace__hint">
            <h3 className="material-caption material-workspace__hint-title">
              💡 프로젝트 기반 작업
            </h3>
            <p className="material-body material-workspace__hint-body">
              각 프로젝트는 독립적인 컨텍스트와 지침 버전 이력을 관리하며, 정책 변경 사항을 추적합니다.
            </p>
          </aside>
        </main>
      </div>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </>
  )
}
