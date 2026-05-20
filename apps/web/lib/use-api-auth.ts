'use client'

import { useAuth } from '@clerk/nextjs'
import { useEffect } from 'react'

import { setAuthTokenGetter } from './api'

/**
 * Wires Clerk's getToken() into the axios instance in lib/api.ts.
 * Mount this once at the top of an authenticated layout (e.g. dashboard layout).
 */
export function useApiAuth(): void {
  const { getToken, isSignedIn } = useAuth()

  useEffect(() => {
    setAuthTokenGetter(async () => (isSignedIn ? await getToken() : null))
  }, [getToken, isSignedIn])
}
