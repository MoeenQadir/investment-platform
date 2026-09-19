'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { brand } from '@/lib/brand'

export default function Header() {
  const pathname = usePathname()
  const { isSignedIn } = useAuth()

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-ink-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 text-sm font-black text-ink-950 shadow-lg shadow-emerald-500/25">
            A
          </span>
          <span>
            <span className="block text-sm font-bold tracking-tight text-white">
              {brand.name}
            </span>
            <span className="block text-[10px] uppercase tracking-widest text-emerald-300/80">
              Research Platform
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {brand.nav.map((item) => {
            const active =
              item.href === '/'
                ? pathname === '/'
                : pathname.startsWith(item.href)
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-emerald-400/10 text-emerald-300'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-3">
          {isSignedIn ? (
            <Link href="/dashboard" className="btn-accent">
              Dashboard
            </Link>
          ) : (
            <Link href="/sign-in" className="btn-accent">
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}