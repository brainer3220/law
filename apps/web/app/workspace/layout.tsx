'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  workspaceClient,
  type Project,
} from '@/lib/workspace/client'
import { useAuth } from '@/lib/auth/AuthContext'
import CreateProjectModal from '@/components/workspace/CreateProjectModal'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import {
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
  PlusIcon,
  RocketLaunchIcon,
  SparklesIcon,
  ArrowLeftIcon,
} from '@heroicons/react/24/outline'

const FALLBACK_USER_ID = '00000000-0000-0000-0000-000000000001'

interface WorkspaceLayoutContextValue {
  projects: Project[]
  projectsLoading: boolean
  projectsError: string | null
  requestUserId: string
  reloadProjects: () => Promise<void>
  openCreateProjectModal: () => void
  closeCreateProjectModal: () => void
  isSidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

const WorkspaceLayoutContext = createContext<WorkspaceLayoutContextValue | null>(null)

export function useWorkspaceLayout() {
  const context = useContext(WorkspaceLayoutContext)
  if (!context) {
    throw new Error('useWorkspaceLayout must be used within WorkspaceLayout')
  }
  return context
}

export default function WorkspaceLayout({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth()
  const pathname = usePathname()
  const router = useRouter()

  const [projects, setProjects] = useState<Project[]>([])
  const [projectsLoading, setProjectsLoading] = useState(true)
  const [projectsError, setProjectsError] = useState<string | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)

  const requestUserId = useMemo(
    () => user?.id || FALLBACK_USER_ID,
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
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      setProjects(sorted)
    } catch (err) {
      console.error('Failed to load projects:', err)
      setProjectsError(
        err instanceof Error
          ? err.message
          : '프로젝트를 불러오는 데 실패했습니다.'
      )
    } finally {
      setProjectsLoading(false)
    }
  }, [requestUserId])

  useEffect(() => {
    if (authLoading || !user) {
      return
    }
    void loadProjects()
  }, [authLoading, user, loadProjects])

  const handleProjectCreated = useCallback(() => {
    void loadProjects()
  }, [loadProjects])

  const openCreateModal = useCallback(() => setIsCreateModalOpen(true), [])
  const closeCreateModal = useCallback(() => setIsCreateModalOpen(false), [])

  const contextValue = useMemo<WorkspaceLayoutContextValue>(
    () => ({
      projects,
      projectsLoading,
      projectsError,
      requestUserId,
      reloadProjects: loadProjects,
      openCreateProjectModal: openCreateModal,
      closeCreateProjectModal: closeCreateModal,
      isSidebarOpen,
      setSidebarOpen: setIsSidebarOpen,
    }),
    [
      projects,
      projectsLoading,
      projectsError,
      requestUserId,
      loadProjects,
      openCreateModal,
      closeCreateModal,
      isSidebarOpen,
    ]
  )

  if (authLoading) {
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
          onClick={() => {
            window.location.href = '/auth/login'
          }}
        >
          로그인하기
        </md-filled-button>
      </div>
    )
  }

  const isProjectRoute =
    pathname?.startsWith('/workspace/') && pathname !== '/workspace'
  const contentClassNames = [
    'material-workspace__content',
    isProjectRoute ? 'material-workspace__content--project' : null,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <WorkspaceLayoutContext.Provider value={contextValue}>
      <div
        className={`material-workspace${
          isSidebarOpen ? '' : ' material-workspace--collapsed'
        }`}
      >
        <aside
          id="workspace-navigation"
          className={`material-workspace__navigation${
            isSidebarOpen ? '' : ' material-workspace__navigation--collapsed'
          }`}
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
                  <ChevronDoubleLeftIcon
                    className="material-workspace__toggle-icon"
                    aria-hidden="true"
                  />
                  <span className="material-visually-hidden">사이드바 닫기</span>
                </button>
                {isProjectRoute && (
                  <button
                    type="button"
                    onClick={() => router.push('/workspace')}
                    className="material-icon-button material-icon-button--tonal material-workspace__back-inline"
                    aria-label="프로젝트 목록으로 이동"
                  >
                    <ArrowLeftIcon className="material-icon" aria-hidden="true" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={openCreateModal}
                  className="material-workspace__create-inline"
                >
                  <span
                    className="material-workspace__create-inline-icon"
                    aria-hidden="true"
                  >
                    <PlusIcon className="material-icon" />
                  </span>
                  <span className="material-workspace__create-inline-label">
                    새 프로젝트
                  </span>
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
                  <ChevronDoubleRightIcon
                    className="material-workspace__compact-toggle-icon"
                    aria-hidden="true"
                  />
                  <span className="material-visually-hidden">사이드바 열기</span>
                </button>
                {isProjectRoute && (
                  <button
                    type="button"
                    onClick={() => router.push('/workspace')}
                    className="material-workspace__compact-action"
                    aria-label="프로젝트 목록으로 이동"
                  >
                    <ArrowLeftIcon className="material-icon" aria-hidden="true" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={openCreateModal}
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
                <SparklesIcon
                  className="material-workspace__title-icon"
                  aria-hidden="true"
                />
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
              <p className="material-workspace__project-error">{projectsError}</p>
            ) : projects.length === 0 ? (
              <p className="material-workspace__project-empty">
                아직 생성된 프로젝트가 없습니다.
              </p>
            ) : (
              <ul className="material-workspace__project-list">
                {projects.map((project) => {
                  const isActive = pathname === `/workspace/${project.id}`
                  const initial =
                    project.name?.charAt(0)?.toUpperCase() || '#'

                  return (
                    <li key={project.id}>
                      <Link
                        href={`/workspace/${project.id}`}
                        className={`material-workspace__project-link${
                          isActive ? ' is-active' : ''
                        }`}
                        aria-label={project.name}
                      >
                        <span
                          className="material-workspace__project-avatar"
                          aria-hidden="true"
                        >
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

        <main className={contentClassNames}>{children}</main>
      </div>

      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={closeCreateModal}
        onSuccess={handleProjectCreated}
      />
    </WorkspaceLayoutContext.Provider>
  )
}
