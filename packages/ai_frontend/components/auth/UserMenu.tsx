'use client'

import { useAuth } from '@/lib/auth/AuthContext'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

export function UserMenu() {
  const { user, signOut } = useAuth()
  const router = useRouter()
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)

  if (!user) {
    return null
  }

  const handleSignOut = async () => {
    setLoading(true)
    try {
      await signOut()
      router.push('/auth/login')
      router.refresh()
    } catch (error) {
      console.error('Error signing out:', error)
    } finally {
      setLoading(false)
      setIsOpen(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 rounded-md px-3 py-2 text-sm font-medium hover:bg-gray-100"
      >
        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
          {user.email?.[0].toUpperCase()}
        </div>
        <span>{user.email}</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-2 w-48 rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5">
            <div className="px-4 py-2 text-sm text-gray-700 border-b">
              {user.user_metadata?.full_name || user.email}
            </div>
            <button
              onClick={handleSignOut}
              disabled={loading}
              className="block w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 disabled:opacity-50"
            >
              {loading ? '로그아웃 중...' : '로그아웃'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
