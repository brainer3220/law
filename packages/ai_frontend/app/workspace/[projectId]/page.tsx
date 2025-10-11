'use client'

/**
 * 프로젝트 상세 페이지 - 지침 버전 관리 중심 뷰
 */

import { use, useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'
import {
  type Instruction,
  type Member,
  type Project,
  workspaceClient,
} from '@/lib/workspace/client'
import { useAuth } from '@/lib/auth/AuthContext'
import {
  ArrowLeftIcon,
  DocumentTextIcon,
  ClockIcon,
  UserGroupIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline'

interface PageProps {
  params: Promise<{ projectId: string }>
}

export default function ProjectDetailPage({ params }: PageProps) {
  const resolvedParams = use(params)
  const { user } = useAuth()
  const [project, setProject] = useState<Project | null>(null)
  const [instructions, setInstructions] = useState<Instruction[]>([])
  const [members, setMembers] = useState<Member[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [newInstruction, setNewInstruction] = useState('')
  const [instructionError, setInstructionError] = useState<string | null>(null)
  const [creatingInstruction, setCreatingInstruction] = useState(false)

  const loadProjectData = useCallback(async () => {
    if (!user?.id) return

    try {
      setLoading(true)
      workspaceClient.setUserId(user.id)

      const [projectData, instructionData, membersData] = await Promise.all([
        workspaceClient.getProject(resolvedParams.projectId),
        workspaceClient.listInstructions(resolvedParams.projectId),
        workspaceClient
          .listMembers(resolvedParams.projectId)
          .catch(() => [] as Member[]),
      ])

      setProject(projectData)
      const sortedInstructions = [...instructionData].sort(
        (a, b) => b.version - a.version
      )
      setInstructions(sortedInstructions)
      setMembers(membersData ?? [])
    } catch (err) {
      console.error('Failed to load project:', err)
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }, [resolvedParams.projectId, user])

  useEffect(() => {
    void loadProjectData()
  }, [loadProjectData])

  const handleInstructionSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!project || !newInstruction.trim()) return

    try {
      setCreatingInstruction(true)
      setInstructionError(null)
      await workspaceClient.createInstruction(project.id, {
        content: newInstruction.trim(),
      })
      setNewInstruction('')
      await loadProjectData()
    } catch (err) {
      console.error('Failed to create instruction:', err)
      setInstructionError(
        err instanceof Error ? err.message : '지침을 저장하지 못했습니다.'
      )
    } finally {
      setCreatingInstruction(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">로딩 중...</p>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-600 dark:text-red-400">
            오류 발생
          </h2>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            {error || '프로젝트를 찾을 수 없습니다'}
          </p>
          <Link
            href="/workspace"
            className="mt-4 inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            프로젝트 목록으로
          </Link>
        </div>
      </div>
    )
  }

  const latestInstruction = instructions[0] ?? null

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-200 dark:bg-slate-900/80 dark:border-gray-800">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-4 flex-1 min-w-0">
              <Link
                href="/workspace"
                className="flex-shrink-0 rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </Link>
              <div className="flex-1 min-w-0">
                <h1 className="text-lg font-bold text-gray-900 dark:text-white truncate">
                  {project.name}
                </h1>
                {project.description && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                    {project.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Stats bar */}
      <div className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-slate-900">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center gap-4 flex-wrap text-xs sm:text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center gap-2">
              <DocumentTextIcon className="h-4 w-4 text-blue-500" />
              <span>
                지침 버전{' '}
                <strong className="text-gray-900 dark:text-white">
                  {latestInstruction ? `v${latestInstruction.version}` : '없음'}
                </strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <ClockIcon className="h-4 w-4 text-gray-400" />
              <span>
                마지막 업데이트:{' '}
                <strong className="text-gray-900 dark:text-white">
                  {format(new Date(project.updated_at), 'yyyy.MM.dd HH:mm', {
                    locale: ko,
                  })}
                </strong>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <UserGroupIcon className="h-4 w-4 text-gray-400" />
              <span>
                멤버 <strong className="text-gray-900 dark:text-white">{members.length}</strong>명
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Instruction composer */}
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-slate-900">
          <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-800">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white">
              <PencilSquareIcon className="h-4 w-4" />
              새 지침 버전 작성
            </h2>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              시스템 프롬프트를 업데이트하면 새로운 버전이 생성됩니다.
            </p>
          </div>
          <form onSubmit={handleInstructionSubmit} className="space-y-3 px-4 py-4">
            <textarea
              value={newInstruction}
              onChange={(event) => setNewInstruction(event.target.value)}
              rows={6}
              placeholder="예: 답변은 존댓말로 작성하고, 근거 법령/판례를 반드시 명시합니다."
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-700 dark:bg-slate-800 dark:text-white dark:placeholder-gray-500"
              disabled={creatingInstruction}
            />
            {instructionError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200">
                {instructionError}
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-gray-400">
                현재 버전은 수정되지 않으며, 항상 새로운 버전을 추가합니다.
              </span>
              <button
                type="submit"
                disabled={creatingInstruction || !newInstruction.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
              >
                {creatingInstruction ? '저장 중...' : '새 버전 저장'}
              </button>
            </div>
          </form>
        </section>

        {/* Instruction history */}
        <section className="space-y-4">
          <header>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              지침 변경 이력
            </h2>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              가장 최근 버전이 상단에 표시됩니다.
            </p>
          </header>

          {instructions.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white px-6 py-8 text-center text-sm text-gray-600 dark:border-gray-700 dark:bg-slate-900 dark:text-gray-400">
              아직 등록된 지침이 없습니다. 상단 입력창에서 첫 지침을 작성해보세요.
            </div>
          ) : (
            <div className="space-y-3">
              {instructions.map((instruction) => (
                <InstructionCard key={instruction.version} instruction={instruction} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function InstructionCard({ instruction }: { instruction: Instruction }) {
  return (
    <article className="group relative rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition hover:border-blue-200 hover:shadow-md dark:border-gray-800 dark:bg-slate-900 dark:hover:border-blue-800/40">
      <div className="absolute left-0 top-0 bottom-0 w-1 rounded-l-lg bg-blue-500 opacity-0 transition-opacity group-hover:opacity-100" />
      <header className="mb-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
            v{instruction.version}
          </span>
          <span>
            {format(new Date(instruction.created_at), 'yyyy년 M월 d일 HH:mm', {
              locale: ko,
            })}
          </span>
        </div>
        <span className="text-[11px] text-gray-400 dark:text-gray-500">
          작성자 {instruction.created_by.slice(0, 8)}…
        </span>
      </header>
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-800 dark:text-gray-200">
        {instruction.content}
      </div>
    </article>
  )
}
