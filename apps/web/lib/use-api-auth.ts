'use client'

import { useAuth } from '@/lib/auth'
import { useEffect } from 'react'

import { setAuthTokenGetter } from './api'

/**
 * Wires the auth getToken() into the axios instance in lib/api.ts.
 * Mount this once at the top of an authenticated layout (e.g. dashboard layout).
 */
export function useApiAuth(): void {
  const { getToken, isSignedIn } = useAuth()

  useEffect(() => {
    setAuthTokenGetter(async () => (isSignedIn ? await getToken() : null))
  }, [getToken, isSignedIn])
}