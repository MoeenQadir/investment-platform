import type { Metadata } from 'next'
import { AuthProvider } from '@/lib/auth'
import Header from '@/components/Header'
import Footer from '@/components/Footer'
import { brand } from '@/lib/brand'
import './globals.css'

export const metadata: Metadata = {
  title: {
    default: `${brand.name} — ${brand.tagline}`,
    template: `%s · ${brand.name}`,
  },
  description: brand.description,
  keywords: [
    'investment research',
    'AI investing',
    'portfolio analytics',
    'SEC filings',
    'insider trading',
    'stock research platform',
  ],
  authors: [{ name: 'Muhammad Moeen Ul Qadir', url: brand.email }],
  openGraph: {
    title: `${brand.name} — ${brand.tagline}`,
    description: brand.description,
    url: brand.domain,
    siteName: brand.name,
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: `${brand.name} — ${brand.tagline}`,
    description: brand.description,
  },
  icons: {
    icon: [
      { url: '/brand-mark.svg', type: 'image/svg+xml' },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <AuthProvider>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </AuthProvider>
      </body>
    </html>
  )
}