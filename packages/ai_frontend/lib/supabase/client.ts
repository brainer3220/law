/**
 * Supabase Browser Client
 * Use this in client components and pages
 */
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  const supabaseUrl = process.env.KIM_BYUN_SUPABASE_URL
  const supabaseAnonKey = process.env.KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      'Missing Supabase environment variables. Please set KIM_BYUN_SUPABASE_URL and KIM_BYUN_NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local'
    )
  }

  return createBrowserClient(supabaseUrl, supabaseAnonKey)
}
