'use client'

import '@material/web/button/filled-button.js'
import '@material/web/button/filled-tonal-button.js'
import '@material/web/button/outlined-button.js'
import '@material/web/iconbutton/filled-tonal-icon-button.js'
import '@material/web/progress/circular-progress.js'

import { use, useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import {
  type Update,
  type Member,
  type Project,
  workspaceClient,
} from '@/lib/workspace/client'
import { useAuth } from '@/lib/auth/AuthContext'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import {
  ArrowLeftIcon,
  DocumentTextIcon,
  ClockIcon,
  UserGroupIcon,
  PencilSquareIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'

interface PageProps {
  params: Promise<{ projectId: string }>
}

export default function ProjectDetailPage({ params }: PageProps) {
  const resolvedParams = use(params)
  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const userId = user?.id ?? null

  const [project, setProject] = useState<Project | null>(null)
  const [updates, setUpdates] = useState<Update[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newUpdate, setNewUpdate] = useState('')
  const [updateError, setUpdateError] = useState<string | null>(null)
  const [creatingUpdate, setCreatingUpdate] = useState(false)
  const [projectDeleteError, setProjectDeleteError] = useState<string | null>(null)
  const [deletingProject, setDeletingProject] = useState(false)
  const [deletingUpdateId, setDeletingUpdateId] = useState<string | null>(null)
  const [updateDeleteError, setUpdateDeleteError] = useState<string | null>(null)

  const sortedUpdates = useMemo(() => {
    return [...updates].sort((a, b) => {
      const aTime = a.created_at ? new Date(a.created_at).getTime() : 0
      const bTime = b.created_at ? new Date(b.created_at).getTime() : 0
      return bTime - aTime
    })
  }, [updates])

  const loadProjectData = useCallback(async () => {
    if (!userId) {
      return
    }

    try {
      setLoading(true)
      workspaceClient.setUserId(userId)

      const [projectData, updateData, membersData] = await Promise.all([
        workspaceClient.getProject(resolvedParams.projectId),
        workspaceClient.listUpdates(resolvedParams.projectId),
        workspaceClient.listMembers(resolvedParams.projectId).catch(() => [] as Member[]),
      ])

      setProject(projectData)
      setUpdates(updateData)
      setMembers(membersData ?? [])
      setError(null)
    } catch (err) {
      console.error('Failed to load project:', err)
      setError(err instanceof Error ? err.message : '프로젝트를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [resolvedParams.projectId, userId])

  useEffect(() => {
    if (userId) {
      void loadProjectData()
    }
  }, [loadProjectData, userId])

  useEffect(() => {
    if (!userId && !authLoading) {
      setLoading(false)
    }
  }, [userId, authLoading])

  const handleDeleteProject = async () => {
    if (!project || !userId) {
      return
    }
    if (
      !window.confirm(
        '이 프로젝트를 삭제하면 모든 멤버의 접근이 차단됩니다. 계속하시겠습니까?'
      )
    ) {
      return
    }
    try {
      setDeletingProject(true)
      setProjectDeleteError(null)
      workspaceClient.setUserId(userId)
      await workspaceClient.deleteProject(project.id)
      router.push('/workspace')
    } catch (err) {
      console.error('Failed to delete project:', err)
      setProjectDeleteError(
        err instanceof Error ? err.message : '프로젝트를 삭제하지 못했습니다.'
      )
    } finally {
      setDeletingProject(false)
    }
  }

  const handleDeleteUpdate = async (updateId: string) => {
    if (!project || !userId) {
      return
    }
    if (!window.confirm('이 업데이트를 삭제하시겠습니까?')) {
      return
    }
    try {
      setDeletingUpdateId(updateId)
      setUpdateDeleteError(null)
      workspaceClient.setUserId(userId)
      await workspaceClient.deleteUpdate(project.id, updateId)
      await loadProjectData()
    } catch (err) {
      console.error('Failed to delete update:', err)
      setUpdateDeleteError(
        err instanceof Error ? err.message : '업데이트를 삭제하지 못했습니다.'
      )
    } finally {
      setDeletingUpdateId(null)
    }
  }

  const handleUpdateSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!project || !newUpdate.trim()) {
      return
    }

    try {
      setCreatingUpdate(true)
      setUpdateError(null)
      await workspaceClient.createUpdate(project.id, {
        body: newUpdate.trim(),
      })
      setNewUpdate('')
      await loadProjectData()
    } catch (err) {
      console.error('Failed to create update:', err)
      setUpdateError(
        err instanceof Error ? err.message : '업데이트를 저장하지 못했습니다.'
      )
    } finally {
      setCreatingUpdate(false)
    }
  }

  if (authLoading) {
    return (
      <div className="material-screen">
        <LoadingSpinner label="세션을 확인하는 중입니다…" />
      </div>
    )
  }

  if (!userId) {
    return (
      <div className="material-empty">
        <h2 className="material-title material-empty__title">로그인이 필요합니다</h2>
        <p className="material-body material-empty__body">
          프로젝트를 확인하려면 먼저 로그인하세요.
        </p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="material-screen">
        <LoadingSpinner label="프로젝트를 불러오는 중입니다…" />
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="material-empty">
        <h2 className="material-title material-empty__title">프로젝트를 찾을 수 없습니다</h2>
        <p className="material-body material-empty__body">
          {error || '선택한 프로젝트가 삭제되었거나 접근 권한이 없습니다.'}
        </p>
        <button
          type="button"
          onClick={() => router.push('/workspace')}
          className="material-filled-button material-filled-button--tonal"
        >
          <ArrowLeftIcon className="material-icon" aria-hidden="true" />
          <span>프로젝트 목록으로</span>
        </button>
      </div>
    )
  }

  const latestUpdate = sortedUpdates[0] ?? null

  return (
    <div className="material-project">
      <header className="material-project__bar">
        <div className="material-project__breadcrumbs">
          <button
            type="button"
            aria-label="프로젝트 목록으로 이동"
            onClick={() => router.push('/workspace')}
            className="material-icon-button material-icon-button--tonal"
          >
            <ArrowLeftIcon className="material-icon" aria-hidden="true" />
          </button>
          <div className="material-project__overview">
            <h1 className="material-title material-project__title">{project.name}</h1>
            {project.description && (
              <p className="material-caption material-project__description">
                {project.description}
              </p>
            )}
          </div>
        </div>
        <div className="material-project__actions">
          {projectDeleteError && (
            <div className="material-alert material-alert--error material-project__error-alert">
              {projectDeleteError}
            </div>
          )}
          <button
            type="button"
            disabled={deletingProject}
            onClick={handleDeleteProject}
            className="material-outlined-button material-outlined-button--error"
          >
            <TrashIcon className="material-icon" aria-hidden="true" />
            <span>{deletingProject ? '삭제 중…' : '프로젝트 삭제'}</span>
          </button>
        </div>
      </header>

      <section className="material-project__stats">
        <StatTile
          icon={<DocumentTextIcon className="material-icon" aria-hidden="true" />}
          label="업데이트"
          value={`${sortedUpdates.length}개`}
        />
        <StatTile
          icon={<ClockIcon className="material-icon" aria-hidden="true" />}
          label="최근 활동"
          value={
            latestUpdate?.created_at
              ? format(new Date(latestUpdate.created_at), 'yyyy.MM.dd HH:mm', {
                  locale: ko,
                })
              : '없음'
          }
        />
        <StatTile
          icon={<UserGroupIcon className="material-icon" aria-hidden="true" />}
          label="멤버"
          value={`${members.length}명`}
        />
      </section>

      <main className="material-project__content">
        <section className="material-project__composer">
          <header className="material-project__section-header">
            <h2 className="material-title material-project__section-title">
              <PencilSquareIcon className="material-icon" aria-hidden="true" />
              프로젝트 업데이트 작성
            </h2>
            <p className="material-caption">
              진행 상황, 결정 사항, 다음 액션 등을 간단히 기록하세요.
            </p>
          </header>

          <form onSubmit={handleUpdateSubmit} className="material-project__form">
            <textarea
              value={newUpdate}
              onChange={(event) => setNewUpdate(event.target.value)}
              rows={6}
              placeholder="예: 주간 브리핑, 장애 대응 현황, 이해관계자에게 공유할 메시지 등을 기록합니다."
              className="material-textarea"
              disabled={creatingUpdate}
            />
            {updateError && (
              <div className="material-alert material-alert--error">{updateError}</div>
            )}
            <div className="material-project__form-footer">
              <span className="material-support-text">
                새로운 업데이트는 타임라인 상단에 바로 노출됩니다.
              </span>
              <button
                type="submit"
                disabled={creatingUpdate || !newUpdate.trim()}
                className="material-filled-button"
              >
                <span>{creatingUpdate ? '기록 중…' : '업데이트 남기기'}</span>
              </button>
            </div>
          </form>
        </section>

        <section className="material-project__timeline">
          <header className="material-project__section-header">
            <h2 className="material-title material-project__section-title">
              업데이트 타임라인
            </h2>
            <p className="material-caption">
              가장 최근 업데이트가 상단에 표시됩니다.
            </p>
          </header>

          {updateDeleteError && (
            <div className="material-alert material-alert--error">{updateDeleteError}</div>
          )}

          {sortedUpdates.length === 0 ? (
            <div className="material-placeholder">
              아직 등록된 업데이트가 없습니다. 상단에서 첫 업데이트를 기록해보세요.
            </div>
          ) : (
            sortedUpdates.map((update) => (
              <UpdateCard
                key={update.id}
                update={update}
                onDelete={() => handleDeleteUpdate(update.id)}
                deleting={deletingUpdateId === update.id}
              />
            ))
          )}
        </section>
      </main>
    </div>
  )
}

function StatTile({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="material-project__stat">
      <span className="material-project__stat-icon">{icon}</span>
      <div>
        <span className="material-caption">{label}</span>
        <p className="material-stat-value">{value}</p>
      </div>
    </div>
  )
}

function UpdateCard({
  update,
  onDelete,
  deleting,
}: {
  update: Update
  onDelete: () => void
  deleting: boolean
}) {
  const createdAt = update.created_at ? new Date(update.created_at) : null

  return (
    <article className="material-update-card">
      <header className="material-update-card__header">
        <div className="material-update-card__meta">
          <span className="material-update-card__badge">Update</span>
          <span className="material-caption">
            {createdAt
              ? format(createdAt, 'yyyy년 M월 d일 HH:mm', {
                  locale: ko,
                })
              : '시간 정보 없음'}
          </span>
        </div>
        {update.created_by && (
          <span className="material-support-text">
            작성자 {update.created_by.slice(0, 8)}…
          </span>
        )}
        <button
          type="button"
          className="material-outlined-button material-outlined-button--small material-update-card__delete"
          disabled={deleting}
          onClick={onDelete}
        >
          <TrashIcon className="material-icon" aria-hidden="true" />
          <span>{deleting ? '삭제 중…' : '삭제'}</span>
        </button>
      </header>
      <div className="material-update-card__body">
        {update.body && update.body.trim().length > 0
          ? update.body
          : '내용이 비어 있습니다.'}
      </div>
    </article>
  )
}
