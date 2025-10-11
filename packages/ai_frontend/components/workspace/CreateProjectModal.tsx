'use client'

/**
 * CreateProjectModal - 프로젝트 생성 모달
 */

import { useState } from 'react'
import { workspaceClient, type ProjectCreate } from '@/lib/workspace/client'
import { useAuth } from '@/lib/auth/AuthContext'
import { XMarkIcon } from '@heroicons/react/24/outline'

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function CreateProjectModal({
  isOpen,
  onClose,
  onSuccess,
}: CreateProjectModalProps) {
  const { user } = useAuth()
  const [formData, setFormData] = useState<ProjectCreate>({
    name: '',
    description: '',
    status: 'active',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user?.id) return

    try {
      setLoading(true)
      setError(null)
      workspaceClient.setUserId(user.id)
      await workspaceClient.createProject(formData)
      setFormData({ name: '', description: '', status: 'active' })
      onSuccess()
      onClose()
    } catch (err) {
      console.error('Failed to create project:', err)
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={handleBackdropClick}
    >
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-slate-900">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            새 프로젝트 만들기
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-slate-800 dark:hover:text-gray-300"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              프로젝트 이름 *
            </label>
            <input
              type="text"
              id="name"
              required
              maxLength={255}
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-700 dark:bg-slate-800 dark:text-white dark:placeholder-gray-500"
              placeholder="예: 계약서 검토 프로젝트"
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              설명
            </label>
            <textarea
              id="description"
              rows={3}
              value={formData.description || ''}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-700 dark:bg-slate-800 dark:text-white dark:placeholder-gray-500"
              placeholder="프로젝트에 대한 간단한 설명을 입력하세요"
            />
          </div>

          {/* Status */}
          <div>
            <label
              htmlFor="status"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              진행 상태
            </label>
            <select
              id="status"
              value={formData.status ?? 'active'}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  status: e.target.value,
                })
              }
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-700 dark:bg-slate-800 dark:text-white"
            >
              <option value="active">진행 중</option>
              <option value="planning">계획 단계</option>
              <option value="blocked">보류</option>
            </select>
          </div>

          {/* Error message */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-800 dark:bg-red-900/20">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:text-gray-300 dark:hover:bg-slate-800"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={loading || !formData.name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              {loading ? '생성 중...' : '프로젝트 만들기'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
