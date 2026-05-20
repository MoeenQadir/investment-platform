'use client'

import { useApiAuth } from '@/lib/use-api-auth'

/**
 * Mounts the Clerk → axios token bridge for every authenticated request.
 * Place once inside <ClerkProvider> in the root layout.
 */
export function AuthBridge({ children }: { children: React.ReactNode }) {
  useApiAuth()
  return <>{children}</>
}
