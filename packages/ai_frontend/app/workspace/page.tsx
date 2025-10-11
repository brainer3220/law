'use client'

import '@material/web/button/filled-button.js'
import '@material/web/button/filled-tonal-button.js'
import '@material/web/progress/circular-progress.js'
import '@material/web/icon/icon.js'

import { useState } from 'react'
import { useAuth } from '@/lib/auth/AuthContext'
import ProjectTimeline from '@/components/workspace/ProjectTimeline'
import CreateProjectModal from '@/components/workspace/CreateProjectModal'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { 
  CheckCircleIcon, 
  PlusIcon, 
  SparklesIcon,
  RocketLaunchIcon,
  LightBulbIcon
} from '@heroicons/react/24/outline'

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
      <div className="material-empty material-empty--auth">
        <div className="material-empty__icon-wrapper">
          <RocketLaunchIcon className="material-empty__icon" aria-hidden="true" />
        </div>
        <h2 className="material-title material-empty__title">로그인이 필요합니다</h2>
        <p className="material-body material-empty__body">
          프로젝트를 보려면 먼저 로그인하세요.
        </p>
        <md-filled-button
          type="button"
          onClick={() => window.location.href = '/auth/login'}
        >
          로그인하기
        </md-filled-button>
      </div>
    )
  }

  return (
    <>
      <div className="material-workspace">
        <header className="material-workspace__bar">
          <div className="material-workspace__heading">
            <div className="material-workspace__title-group">
              <SparklesIcon className="material-workspace__title-icon" aria-hidden="true" />
              <h1 className="material-title">프로젝트</h1>
            </div>
            <p className="material-caption">프로젝트 중심 컨텍스트 관리</p>
          </div>
          <button
            type="button"
            onClick={() => setIsCreateModalOpen(true)}
            className="material-filled-button material-workspace__create-button"
          >
            <PlusIcon className="material-icon" aria-hidden="true" />
            <span>새 프로젝트</span>
          </button>
        </header>

        <main className="material-workspace__content">
          <section className="material-workspace__surface">
            <div className="material-workspace__surface-header">
              <div className="material-workspace__status">
                <CheckCircleIcon className="material-icon" aria-hidden="true" />
                <span className="material-caption">On track</span>
              </div>
            </div>
            <ProjectTimeline key={refreshKey} />
          </section>

          <aside className="material-workspace__sidebar">
            <div className="material-workspace__hint">
              <div className="material-workspace__hint-icon">
                <LightBulbIcon className="material-icon" aria-hidden="true" />
              </div>
              <div className="material-workspace__hint-content">
                <h3 className="material-caption material-workspace__hint-title">
                  프로젝트 기반 작업
                </h3>
                <p className="material-body material-workspace__hint-body">
                  각 프로젝트는 독립적인 컨텍스트와 지침 버전 이력을 관리하며, 정책 변경 사항을 추적합니다.
                </p>
              </div>
            </div>

            <div className="material-workspace__quick-tips">
              <h4 className="material-workspace__tips-title">빠른 팁</h4>
              <ul className="material-workspace__tips-list">
                <li>
                  <span className="material-workspace__tip-emoji">📋</span>
                  <span>프로젝트를 클릭하여 상세 정보 확인</span>
                </li>
                <li>
                  <span className="material-workspace__tip-emoji">✏️</span>
                  <span>업데이트로 진행 상황 기록</span>
                </li>
                <li>
                  <span className="material-workspace__tip-emoji">👥</span>
                  <span>팀원 초대로 협업 시작</span>
                </li>
              </ul>
            </div>
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
