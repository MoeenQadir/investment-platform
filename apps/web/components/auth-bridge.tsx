'use client'

import { useApiAuth } from '@/lib/use-api-auth'

/**
 * Mounts the auth → axios token bridge for every authenticated request.
 * Place once inside the app auth provider in the root layout.
 */
export function AuthBridge({ children }: { children: React.ReactNode }) {
  useApiAuth()
  return <>{children}</>
}