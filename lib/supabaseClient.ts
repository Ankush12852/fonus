import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.error("ENVIRONMENT VARIABLE MISSING: NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY is not defined in the frontend. You may need to restart your Next.js dev server.")
}

export const supabase = createClient(supabaseUrl || 'http://missing-url.com', supabaseAnonKey || 'missing-key')
