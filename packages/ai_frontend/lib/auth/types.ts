/**
 * Authentication related TypeScript types
 */

import type { User } from '@supabase/supabase-js'

export interface AuthUser {
  id: string
  email?: string
  full_name?: string
  avatar_url?: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface SignupCredentials extends LoginCredentials {
  fullName?: string
}

export interface AuthResponse {
  user?: AuthUser | null
  session?: any
  error?: string
  message?: string
}

export interface AuthContextType {
  user: User | null
  loading: boolean
  signOut: () => Promise<void>
  refreshUser: () => Promise<void>
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordUpdateRequest {
  password: string
  confirmPassword?: string
}
