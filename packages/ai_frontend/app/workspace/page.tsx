'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/lib/auth/AuthContext'
import ProjectTimeline from '@/components/workspace/ProjectTimeline'
import CreateProjectModal from '@/components/workspace/CreateProjectModal'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { 
  CheckCircleIcon, 
  PlusIcon, 
  SparklesIcon,
  RocketLaunchIcon,
  LightBulbIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon
} from '@heroicons/react/24/outline'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  workspaceClient,
  type Project
} from '@/lib/workspace/client'

export default function WorkspacePage() {
  const { user, loading } = useAuth()
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [projects, setProjects] = useState<Project[]>([])
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [projectsError, setProjectsError] = useState<string | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const pathname = usePathname()

  const requestUserId = useMemo(
    () => user?.id || '00000000-0000-0000-0000-000000000001',
    [user?.id]
  )

  const loadProjects = useCallback(async () => {
    try {
      setProjectsLoading(true)
      setProjectsError(null)
      workspaceClient.setUserId(requestUserId)
      const { projects: projectList } = await workspaceClient.listProjects({
        archived: false,
        limit: 50,
      })
      const sorted = [...projectList].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      setProjects(sorted)
    } catch (err) {
      console.error('Failed to load projects:', err)
      setProjectsError(err instanceof Error ? err.message : '프로젝트를 불러오는 데 실패했습니다.')
    } finally {
      setProjectsLoading(false)
    }
  }, [requestUserId])

  useEffect(() => {
    if (loading || !user) {
      return
    }
    void loadProjects()
  }, [loading, user, loadProjects])

  const handleProjectCreated = () => {
    void loadProjects()
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
      <div className={`material-workspace${isSidebarOpen ? '' : ' material-workspace--collapsed'}`}>
        <aside
          id="workspace-navigation"
          className={`material-workspace__navigation${isSidebarOpen ? '' : ' material-workspace__navigation--collapsed'}`}
          aria-expanded={isSidebarOpen}
        >
          <div className="material-workspace__pinned">
            {isSidebarOpen ? (
              <>
                <button
                  type="button"
                  onClick={() => setIsSidebarOpen(false)}
                  className="material-workspace__toggle"
                  aria-label="사이드바 닫기"
                  aria-controls="workspace-navigation"
                >
                  <ChevronDoubleLeftIcon className="material-workspace__toggle-icon" aria-hidden="true" />
                  <span className="material-visually-hidden">사이드바 닫기</span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(true)}
                  className="material-workspace__create-inline"
                >
                  <span className="material-workspace__create-inline-icon" aria-hidden="true">
                    <PlusIcon className="material-icon" />
                  </span>
                  <span className="material-workspace__create-inline-label">새 프로젝트</span>
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => setIsSidebarOpen(true)}
                  className="material-workspace__compact-toggle"
                  aria-label="사이드바 열기"
                >
                  <ChevronDoubleRightIcon className="material-workspace__compact-toggle-icon" aria-hidden="true" />
                  <span className="material-visually-hidden">사이드바 열기</span>
                </button>
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(true)}
                  className="material-workspace__compact-action"
                  aria-label="새 프로젝트 만들기"
                >
                  <PlusIcon className="material-icon" aria-hidden="true" />
                </button>
              </>
            )}
          </div>

          {isSidebarOpen && (
            <div className="material-workspace__heading">
              <div className="material-workspace__title-group">
                <SparklesIcon className="material-workspace__title-icon" aria-hidden="true" />
                <h1 className="material-title">프로젝트</h1>
              </div>
              <p className="material-caption">프로젝트 중심 컨텍스트 관리</p>
            </div>
          )}

          <nav
            aria-label="프로젝트 목록"
            className="material-workspace__project-list-wrapper"
          >
            {projectsLoading ? (
              <div className="material-workspace__project-loading">
                <LoadingSpinner size="sm" label="프로젝트 로딩 중" />
              </div>
            ) : projectsError ? (
              <p className="material-workspace__project-error">
                {projectsError}
              </p>
            ) : projects.length === 0 ? (
              <p className="material-workspace__project-empty">
                아직 생성된 프로젝트가 없습니다.
              </p>
            ) : (
              <ul className="material-workspace__project-list">
                {projects.map((project) => {
                  const isActive = pathname === `/workspace/${project.id}`
                  const initial = project.name?.charAt(0)?.toUpperCase() || '#'

                  return (
                    <li key={project.id}>
                      <Link
                        href={`/workspace/${project.id}`}
                        className={`material-workspace__project-link${isActive ? ' is-active' : ''}`}
                        aria-label={project.name}
                      >
                        <span className="material-workspace__project-avatar" aria-hidden="true">
                          {initial}
                        </span>
                        <span className="material-workspace__project-meta">
                          <span className="material-workspace__project-name">
                            {project.name}
                          </span>
                          {project.description && (
                            <span className="material-workspace__project-description">
                              {project.description}
                            </span>
                          )}
                        </span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </nav>
        </aside>

        <main className="material-workspace__content">
          <section className="material-workspace__surface">
            <div className="material-workspace__surface-header">
              <div className="material-workspace__status">
                <CheckCircleIcon className="material-icon" aria-hidden="true" />
                <span className="material-caption">On track</span>
              </div>
            </div>
            <ProjectTimeline
              projects={projects}
              loading={projectsLoading}
              error={projectsError}
              userId={requestUserId}
            />
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
