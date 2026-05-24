import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import { AuthBridge } from '@/components/auth-bridge'
import './globals.css'

export const metadata: Metadata = {
  title: 'Investment Research Platform',
  description: 'AI-powered investment research and explanation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <ClerkProvider>
          <AuthBridge>{children}</AuthBridge>
        </ClerkProvider>
      </body>
    </html>
  )
}

