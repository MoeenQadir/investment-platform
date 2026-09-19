'use client'

import { createContext, useContext } from 'react'
import { ClerkProvider, useAuth as useClerkAuth } from '@clerk/nextjs'
import { AuthBridge } from '@/components/auth-bridge'

export type AppAuth = {
  isSignedIn: boolean
  userId: string | null
  getToken: () => Promise<string | null>
}

const isClerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY)

const AppAuthContext = createContext<AppAuth>({
  isSignedIn: false,
  userId: null,
  getToken: async () => null,
})

export function useAuth(): AppAuth {
  return useContext(AppAuthContext)
}

function ClerkAuthBridge({ children }: { children: React.ReactNode }) {
  const { isSignedIn, userId, getToken } = useClerkAuth()
  return (
    <AppAuthContext.Provider
      value={{ isSignedIn: isSignedIn === true, userId: userId ?? null, getToken }}
    >
      <AuthBridge>{children}</AuthBridge>
    </AppAuthContext.Provider>
  )
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  if (!isClerkConfigured) {
    return (
      <AppAuthContext.Provider
        value={{ isSignedIn: false, userId: null, getToken: async () => null }}
      >
        {children}
      </AppAuthContext.Provider>
    )
  }

  return (
    <ClerkProvider>
      <ClerkAuthBridge>{children}</ClerkAuthBridge>
    </ClerkProvider>
  )
}