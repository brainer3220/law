'use client'

/**
 * ProjectTimeline - 프로젝트 타임라인 뷰
 * 최신 항목이 위에 표시되는 타임라인 스타일 UI
 */

import { useEffect, useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'
import {
  type ProjectListItem,
  workspaceClient,
} from '@/lib/workspace/client'
import { useAuth } from '@/lib/auth/AuthContext'
import Link from 'next/link'
import {
  FolderIcon,
  ClockIcon,
  UserIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'

export default function ProjectTimeline() {
  const { user } = useAuth()
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadProjects() {
      if (!user?.id) return

      try {
        setLoading(true)
        workspaceClient.setUserId(user.id)
        const data = await workspaceClient.listProjects({
          archived: false,
          limit: 50,
        })
        // 최신 순으로 정렬 (created_at 기준)
        const sorted = data.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
        setProjects(sorted)
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
        />
      ))}
    </div>
  )
}

interface ProjectTimelineItemProps {
  project: ProjectListItem
}

function ProjectTimelineItem({ project }: ProjectTimelineItemProps) {
  const timeAgo = formatDistanceToNow(new Date(project.created_at), {
    addSuffix: true,
    locale: ko,
  })

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
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
              <span className="text-xs font-medium text-green-600 dark:text-green-400">
                On track
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
              <UserIcon className="h-4 w-4" />
              <span>
                {project.member_count || 0}명
              </span>
            </div>
            <div className="flex items-center gap-1">
              <ClockIcon className="h-4 w-4" />
              <span>{timeAgo}</span>
            </div>
            {project.file_count !== undefined && project.file_count > 0 && (
              <div className="flex items-center gap-1">
                <FolderIcon className="h-4 w-4" />
                <span>{project.file_count}개 파일</span>
              </div>
            )}
          </div>
        </div>

        {/* Preview image placeholder (if needed) */}
        {/* You can add thumbnail or preview here similar to the screenshot */}
      </div>
    </Link>
  )
}
