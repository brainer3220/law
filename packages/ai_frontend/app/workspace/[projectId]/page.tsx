'use client'

/**
 * 프로젝트 상세 페이지 - 타임라인 스타일
 * 글 작성 및 파일 업로드 기능 포함
 */

import { use, useEffect, useState, useRef, useCallback } from 'react'
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
  PaperClipIcon,
  PaperAirplaneIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { format } from 'date-fns'
import { ko } from 'date-fns/locale'

type TimelineItem = {
  id: string
  type: 'file' | 'chat' | 'memory'
  title: string
  description?: string
  timestamp: Date
  data: File | Chat | Memory
}

interface PageProps {
  params: Promise<{ projectId: string }>
}

export default function ProjectDetailPage({ params }: PageProps) {
  const resolvedParams = use(params)
  const { user } = useAuth()
  const [project, setProject] = useState<Project | null>(null)
  const [timelineItems, setTimelineItems] = useState<TimelineItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'file' | 'chat' | 'memory'>('all')
  
  // 입력 상태
  const [inputText, setInputText] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<globalThis.File[]>([])
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadProjectData = useCallback(async () => {
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

      // 타임라인 아이템 생성
      const items: TimelineItem[] = []

      // 파일 추가
      filesData.forEach((file) => {
        items.push({
          id: file.id,
          type: 'file',
          title: file.filename,
          description: `${(file.size_bytes / 1024 / 1024).toFixed(2)} MB`,
          timestamp: new Date(file.uploaded_at),
          data: file,
        })
      })

      // 채팅 추가
      chatsData.forEach((chat) => {
        items.push({
          id: chat.id,
          type: 'chat',
          title: chat.title || '채팅',
          timestamp: new Date(chat.created_at),
          data: chat,
        })
      })

      // 메모리 추가
      memoriesData.forEach((memory) => {
        items.push({
          id: memory.id,
          type: 'memory',
          title: memory.key,
          description: memory.value,
          timestamp: new Date(memory.created_at),
          data: memory,
        })
      })

      // 최신순 정렬
      items.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      setTimelineItems(items)
    } catch (err) {
      console.error('Failed to load project:', err)
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setLoading(false)
    }
  }, [user, resolvedParams.projectId])

  useEffect(() => {
    loadProjectData()
  }, [loadProjectData])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files))
    }
  }

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(selectedFiles.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputText.trim() && selectedFiles.length === 0) return

    try {
      setUploading(true)

      // 파일 업로드
      if (selectedFiles.length > 0) {
        for (const file of selectedFiles) {
          await workspaceClient.uploadFile(resolvedParams.projectId, file)
        }
      }

      // 텍스트가 있으면 채팅으로 저장
      if (inputText.trim()) {
        await workspaceClient.createChat(resolvedParams.projectId, inputText)
      }

      // 입력 초기화
      setInputText('')
      setSelectedFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      // 데이터 새로고침 (페이지 리로드 없이)
      await loadProjectData()
    } catch (err) {
      console.error('Failed to submit:', err)
      alert('업로드 실패: ' + (err instanceof Error ? err.message : '알 수 없는 오류'))
    } finally {
      setUploading(false)
    }
  }

  const filteredItems =
    filter === 'all'
      ? timelineItems
      : timelineItems.filter((item) => item.type === filter)

  const stats = {
    files: timelineItems.filter((i) => i.type === 'file').length,
    chats: timelineItems.filter((i) => i.type === 'chat').length,
    memories: timelineItems.filter((i) => i.type === 'memory').length,
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
          <div className="flex items-center gap-2 flex-wrap text-sm">
            <button
              onClick={() => setFilter('all')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors ${
                filter === 'all'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800'
              }`}
            >
              <span>전체</span>
              <span className="font-medium">{timelineItems.length}</span>
            </button>
            <button
              onClick={() => setFilter('file')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors ${
                filter === 'file'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800'
              }`}
            >
              <DocumentIcon className="h-4 w-4" />
              <span>{stats.files}</span>
            </button>
            <button
              onClick={() => setFilter('chat')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors ${
                filter === 'chat'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800'
              }`}
            >
              <ChatBubbleLeftIcon className="h-4 w-4" />
              <span>{stats.chats}</span>
            </button>
            <button
              onClick={() => setFilter('memory')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full transition-colors ${
                filter === 'memory'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                  : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-slate-800'
              }`}
            >
              <LightBulbIcon className="h-4 w-4" />
              <span>{stats.memories}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <main className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-6">
        {/* Input area */}
        <form onSubmit={handleSubmit} className="mb-6">
          <div className="bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
            {/* Selected files */}
            {selectedFiles.length > 0 && (
              <div className="border-b border-gray-200 dark:border-gray-800 p-3 bg-gray-50 dark:bg-slate-800/50">
                <div className="flex flex-wrap gap-2">
                  {selectedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 bg-white dark:bg-slate-900 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-1.5 text-sm"
                    >
                      <DocumentIcon className="h-4 w-4 text-gray-400" />
                      <span className="text-gray-700 dark:text-gray-300 max-w-[200px] truncate">
                        {file.name}
                      </span>
                      <span className="text-gray-500 dark:text-gray-400 text-xs">
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(index)}
                        className="ml-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400"
                      >
                        <XMarkIcon className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Text input */}
            <div className="relative">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="프로젝트에 대해 작성하거나 파일을 업로드하세요..."
                className="w-full px-4 py-3 bg-transparent border-none resize-none focus:outline-none focus:ring-0 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                rows={3}
                disabled={uploading}
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-slate-800/50">
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-upload"
                  disabled={uploading}
                />
                <label
                  htmlFor="file-upload"
                  className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm font-medium transition-colors ${
                    uploading
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-white dark:bg-slate-900 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 cursor-pointer'
                  }`}
                >
                  <PaperClipIcon className="h-4 w-4" />
                  파일 첨부
                </label>
              </div>

              <button
                type="submit"
                disabled={uploading || (!inputText.trim() && selectedFiles.length === 0)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors"
              >
                {uploading ? (
                  <>
                    <div className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-white border-r-transparent" />
                    업로드 중...
                  </>
                ) : (
                  <>
                    <PaperAirplaneIcon className="h-4 w-4" />
                    작성
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Timeline */}
        {filteredItems.length === 0 ? (
          <div className="text-center py-16 bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-gray-800">
            <div className="flex justify-center mb-4">
              {filter === 'file' && <DocumentIcon className="h-16 w-16 text-gray-300 dark:text-gray-700" />}
              {filter === 'chat' && <ChatBubbleLeftIcon className="h-16 w-16 text-gray-300 dark:text-gray-700" />}
              {filter === 'memory' && <LightBulbIcon className="h-16 w-16 text-gray-300 dark:text-gray-700" />}
              {filter === 'all' && <DocumentIcon className="h-16 w-16 text-gray-300 dark:text-gray-700" />}
            </div>
            <p className="text-gray-600 dark:text-gray-400">
              {filter === 'all' ? '아직 활동이 없습니다' : '해당 항목이 없습니다'}
            </p>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
              위의 입력창에서 글을 작성하거나 파일을 업로드해보세요
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredItems.map((item) => (
              <TimelineItemCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function TimelineItemCard({ item }: { item: TimelineItem }) {
  const icon = {
    file: DocumentIcon,
    chat: ChatBubbleLeftIcon,
    memory: LightBulbIcon,
  }[item.type]

  const bgColor = {
    file: 'bg-blue-100 dark:bg-blue-900/30',
    chat: 'bg-green-100 dark:bg-green-900/30',
    memory: 'bg-purple-100 dark:bg-purple-900/30',
  }[item.type]

  const iconColor = {
    file: 'text-blue-600 dark:text-blue-400',
    chat: 'text-green-600 dark:text-green-400',
    memory: 'text-purple-600 dark:text-purple-400',
  }[item.type]

  const typeLabel = {
    file: '파일',
    chat: '채팅',
    memory: '메모리',
  }[item.type]

  const Icon = icon

  return (
    <div className="group relative bg-white dark:bg-slate-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4 hover:shadow-md transition-all duration-200">
      {/* Hover indicator */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 to-blue-600 rounded-l-lg opacity-0 group-hover:opacity-100 transition-opacity" />

      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`flex-shrink-0 rounded-lg p-2 ${bgColor}`}>
          <Icon className={`h-5 w-5 ${iconColor}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
              {typeLabel}
            </span>
            <span className="text-xs text-gray-400 dark:text-gray-600">•</span>
            <time className="text-xs text-gray-500 dark:text-gray-400">
              {format(item.timestamp, 'yyyy년 M월 d일 HH:mm', { locale: ko })}
            </time>
          </div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
            {item.title}
          </h3>
          {item.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
              {item.description}
            </p>
          )}
          {item.type === 'file' && <FileDetails file={item.data as File} />}
          {item.type === 'memory' && <MemoryDetails memory={item.data as Memory} />}
        </div>
      </div>
    </div>
  )
}

function FileDetails({ file }: { file: File }) {
  return (
    <div className="mt-2 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
      {file.indexed && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
          <span className="h-1.5 w-1.5 rounded-full bg-green-600 dark:bg-green-400" />
          인덱싱됨
        </span>
      )}
    </div>
  )
}

function MemoryDetails({ memory }: { memory: Memory }) {
  const typeColors: Record<string, string> = {
    fact: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    preference:
      'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    context: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    decision:
      'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  }

  return (
    <div className="mt-2">
      <span
        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
          typeColors[memory.memory_type] || typeColors.fact
        }`}
      >
        {memory.memory_type}
      </span>
    </div>
  )
}
