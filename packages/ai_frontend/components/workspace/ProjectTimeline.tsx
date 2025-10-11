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
import { useAuth } from '@/lib/auth/AuthContext'
import Link from 'next/link'
import {
  FolderIcon,
  ClockIcon,
  DocumentTextIcon,
  UserIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'

export default function ProjectTimeline() {
  const { user } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [latestInstructions, setLatestInstructions] = useState<Record<string, Instruction | null>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadProjects() {
      // Use demo user ID if no user is logged in (for development)
      const userId = user?.id || '00000000-0000-0000-0000-000000000001'

      try {
        setLoading(true)
        workspaceClient.setUserId(userId)
        const { projects: projectList } = await workspaceClient.listProjects({
          archived: false,
          limit: 50,
        })
        // 최신 업데이트 순으로 정렬
        const sorted = [...projectList].sort(
          (a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        )
        setProjects(sorted)

        // 프로젝트별 최신 지침 버전 로드
        const entries = await Promise.all(
          sorted.map(async (project) => {
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
        setLatestInstructions(Object.fromEntries(entries))
      } catch (err) {
        console.error('Failed to load projects:', err)
        setError(err instanceof Error ? err.message : 'Failed to load projects')
      } finally {
        setLoading(false)
      }
    }

    loadProjects()
  }, [user])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
            프로젝트를 불러오는 중...
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20">
        <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-12">
        <FolderIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-white">
          프로젝트가 없습니다
        </h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
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
