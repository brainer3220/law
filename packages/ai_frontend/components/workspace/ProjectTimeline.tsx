'use client'

/**
 * ProjectTimeline - 프로젝트 타임라인 뷰
 * 최신 항목이 위에 표시되는 타임라인 스타일 UI
 */

import { useEffect, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'
import {
  type Instruction,
  type Project,
  workspaceClient,
} from '@/lib/workspace/client'
import Link from 'next/link'
import {
  FolderIcon,
  ClockIcon,
  DocumentTextIcon,
  UserIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'

type ProjectTimelineProps = {
  projects: Project[]
  loading: boolean
  error: string | null
  userId: string
}

export default function ProjectTimeline({
  projects,
  loading,
  error,
  userId,
}: ProjectTimelineProps) {
  const [latestInstructions, setLatestInstructions] = useState<Record<string, Instruction | null>>({})
  const [instructionsLoading, setInstructionsLoading] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadInstructions() {
      if (projects.length === 0) {
        setLatestInstructions({})
        setInstructionsLoading(false)
        return
      }

      try {
        setInstructionsLoading(true)
        workspaceClient.setUserId(userId)
        const entries = await Promise.all(
          projects.map(async (project) => {
            try {
              const instructions = await workspaceClient.listInstructions(project.id)
              if (instructions.length === 0) {
                return [project.id, null] as const
              }
              const latest = [...instructions].sort((a, b) => b.version - a.version)[0]
              return [project.id, latest] as const
            } catch (instructionError) {
              console.error(`Failed to load instructions for project ${project.id}:`, instructionError)
              return [project.id, null] as const
            }
          })
        )
        if (!cancelled) {
          setLatestInstructions(Object.fromEntries(entries))
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Failed to load project instructions:', err)
          setLatestInstructions({})
        }
      } finally {
        if (!cancelled) {
          setInstructionsLoading(false)
        }
      }
    }

    void loadInstructions()

    return () => {
      cancelled = true
    }
  }, [projects, userId])

  if (loading || (instructionsLoading && projects.length === 0)) {
    return (
      <div className="project-timeline-loading">
        <div className="project-timeline-spinner">
          <div className="spinner-ring"></div>
          <p className="spinner-text">프로젝트를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="project-timeline-error">
        <svg className="error-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
        <p className="error-text">{error}</p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="project-timeline-empty">
        <div className="empty-icon-wrapper">
          <FolderIcon className="empty-icon" />
        </div>
        <h3 className="empty-title">프로젝트가 없습니다</h3>
        <p className="empty-body">
          새 프로젝트를 만들어 시작하세요.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {projects.map((project) => (
        <ProjectTimelineItem
          key={project.id}
          project={project}
          latestInstruction={latestInstructions[project.id]}
        />
      ))}
    </div>
  )
}

function ProjectTimelineItem({
  project,
  latestInstruction,
}: {
  project: Project
  latestInstruction?: Instruction | null
}) {
  const lastUpdatedAgo = formatDistanceToNow(new Date(project.updated_at), {
    addSuffix: true,
    locale: ko,
  })
  const instructionUpdatedAgo =
    latestInstruction &&
    formatDistanceToNow(new Date(latestInstruction.created_at), {
      addSuffix: true,
      locale: ko,
    })
  const instructionPreview =
    latestInstruction?.content.slice(0, 160).replace(/\s+/g, ' ') ?? '등록된 지침이 없습니다.'
  const statusLabel =
    project.status === 'planning'
      ? '계획 단계'
      : project.status === 'blocked'
        ? '보류'
        : '진행 중'
  const statusBadgeColor =
    project.status === 'blocked'
      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
      : project.status === 'planning'
        ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
        : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'

  return (
    <Link
      href={`/workspace/${project.id}`}
      className="block border-b border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-slate-900/50 transition-colors"
    >
      <div className="px-6 py-4">
        {/* Status indicator */}
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="flex items-center gap-2">
              <CheckCircleIcon
                className={`h-5 w-5 ${project.archived ? 'text-gray-400' : 'text-green-500'}`}
              />
              <span className="text-xs font-medium text-green-600 dark:text-green-400">
                {project.archived ? 'Archived' : 'Active'}
              </span>
            </div>
          </div>
        </div>

        {/* Project info */}
        <div className="mt-3">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white truncate">
                {project.name}
              </h3>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusBadgeColor}`}
                >
                  {statusLabel}
                </span>
              </div>
              {project.description && (
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                  {project.description}
                </p>
              )}
            </div>
          </div>

          {/* Meta info */}
          <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-1">
              <ClockIcon className="h-4 w-4" />
              <span>{lastUpdatedAgo}</span>
            </div>
            {latestInstruction ? (
              <div className="flex items-center gap-1">
                <DocumentTextIcon className="h-4 w-4" />
                <span>지침 v{latestInstruction.version}</span>
                {instructionUpdatedAgo && (
                  <span className="text-gray-400">{instructionUpdatedAgo}</span>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-1">
                <UserIcon className="h-4 w-4" />
                <span>지침 미등록</span>
              </div>
            )}
          </div>
        </div>

        {/* Instruction preview */}
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
          {instructionPreview}
          {latestInstruction && latestInstruction.content.length > 160 && '…'}
        </p>
      </div>
    </Link>
  )
}
