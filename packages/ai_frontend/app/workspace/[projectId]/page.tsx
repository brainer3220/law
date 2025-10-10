'use client'

/**
 * 프로젝트 상세 페이지
 * 프로젝트 내 파일, 채팅, 메모리 등 관리
 */

import { use, useEffect, useState } from 'react'
import { useAuth } from '@/lib/auth/AuthContext'
import {
  workspaceClient,
  type Project,
  type File,
  type Chat,
  type Memory,
} from '@/lib/workspace/client'
import Link from 'next/link'
import {
  ArrowLeftIcon,
  DocumentIcon,
  ChatBubbleLeftIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline'
import { formatDistanceToNow } from 'date-fns'
import { ko } from 'date-fns/locale'

interface PageProps {
  params: Promise<{ projectId: string }>
}

export default function ProjectDetailPage({ params }: PageProps) {
  const resolvedParams = use(params)
  const { user } = useAuth()
  const [project, setProject] = useState<Project | null>(null)
  const [files, setFiles] = useState<File[]>([])
  const [chats, setChats] = useState<Chat[]>([])
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'files' | 'chats' | 'memories'>('files')

  useEffect(() => {
    async function loadProjectData() {
      if (!user?.id) return

      try {
        setLoading(true)
        workspaceClient.setUserId(user.id)

        const [projectData, filesData, chatsData, memoriesData] = await Promise.all([
          workspaceClient.getProject(resolvedParams.projectId),
          workspaceClient.listFiles(resolvedParams.projectId),
          workspaceClient.listChats(resolvedParams.projectId),
          workspaceClient.listMemories(resolvedParams.projectId),
        ])

        setProject(projectData)
        setFiles(filesData.sort((a: File, b: File) => 
          new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime()
        ))
        setChats(chatsData.sort((a: Chat, b: Chat) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ))
        setMemories(memoriesData.sort((a: Memory, b: Memory) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        ))
      } catch (err) {
        console.error('Failed to load project:', err)
        setError(err instanceof Error ? err.message : 'Failed to load project')
      } finally {
        setLoading(false)
      }
    }

    loadProjectData()
  }, [user, resolvedParams.projectId])

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

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-gray-200 dark:bg-slate-900/80 dark:border-gray-800">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/workspace"
                className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800"
              >
                <ArrowLeftIcon className="h-5 w-5" />
              </Link>
              <div>
                <h1 className="text-lg font-bold text-gray-900 dark:text-white">
                  {project.name}
                </h1>
                {project.description && (
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {project.description}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="border-b border-gray-200 dark:border-gray-800">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('files')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'files'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                <DocumentIcon className="h-5 w-5" />
                파일 ({files.length})
              </button>
              <button
                onClick={() => setActiveTab('chats')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'chats'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                <ChatBubbleLeftIcon className="h-5 w-5" />
                채팅 ({chats.length})
              </button>
              <button
                onClick={() => setActiveTab('memories')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'memories'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-200'
                }`}
              >
                <LightBulbIcon className="h-5 w-5" />
                메모리 ({memories.length})
              </button>
            </nav>
          </div>

          {/* Tab content */}
          <div className="p-6">
            {activeTab === 'files' && (
              <FilesList files={files} />
            )}
            {activeTab === 'chats' && (
              <ChatsList chats={chats} />
            )}
            {activeTab === 'memories' && (
              <MemoriesList memories={memories} />
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function FilesList({ files }: { files: File[] }) {
  if (files.length === 0) {
    return (
      <div className="text-center py-8">
        <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          업로드된 파일이 없습니다
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {files.map((file) => {
        const timeAgo = formatDistanceToNow(new Date(file.uploaded_at), {
          addSuffix: true,
          locale: ko,
        })
        const sizeMB = (file.size_bytes / 1024 / 1024).toFixed(2)

        return (
          <div
            key={file.id}
            className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-slate-800/50"
          >
            <div className="flex items-center gap-3">
              <DocumentIcon className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {file.filename}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {sizeMB} MB · {timeAgo}
                  {file.indexed && (
                    <span className="ml-2 text-green-600 dark:text-green-400">
                      ✓ 인덱싱됨
                    </span>
                  )}
                </p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ChatsList({ chats }: { chats: Chat[] }) {
  if (chats.length === 0) {
    return (
      <div className="text-center py-8">
        <ChatBubbleLeftIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          채팅 기록이 없습니다
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {chats.map((chat) => {
        const timeAgo = formatDistanceToNow(new Date(chat.created_at), {
          addSuffix: true,
          locale: ko,
        })

        return (
          <div
            key={chat.id}
            className="flex items-center justify-between p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-slate-800/50"
          >
            <div className="flex items-center gap-3">
              <ChatBubbleLeftIcon className="h-5 w-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {chat.title || '제목 없음'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {timeAgo}
                </p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function MemoriesList({
  memories,
}: {
  memories: Memory[]
}) {
  if (memories.length === 0) {
    return (
      <div className="text-center py-8">
        <LightBulbIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          저장된 메모리가 없습니다
        </p>
      </div>
    )
  }

  const typeColors: Record<string, string> = {
    fact: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    preference: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    context: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    decision: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  }

  return (
    <div className="space-y-2">
      {memories.map((memory) => {
        const timeAgo = formatDistanceToNow(new Date(memory.created_at), {
          addSuffix: true,
          locale: ko,
        })

        return (
          <div
            key={memory.id}
            className="p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-slate-800/50"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      typeColors[memory.memory_type] || typeColors.fact
                    }`}
                  >
                    {memory.memory_type}
                  </span>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {memory.key}
                  </p>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {memory.value}
                </p>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
                  {timeAgo}
                </p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
