import { SignIn } from '@clerk/nextjs'
import { brand } from '@/lib/brand'
import Link from 'next/link'

const isClerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY)

export default function SignInPage() {
  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md text-center">
        <Link href="/" className="mb-6 inline-flex items-center gap-2.5">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 text-base font-black text-ink-950 shadow-lg shadow-emerald-500/25">
            A
          </span>
          <span className="text-xl font-bold text-white">{brand.name}</span>
        </Link>
        <p className="mb-6 text-sm text-slate-400">{brand.tagline}</p>
        {isClerkConfigured ? (
          <div className="glass-card p-2">
            <div className="flex flex-col items-center">
              <SignIn />
            </div>
          </div>
        ) : (
          <div className="glass-card p-10">
            <p className="text-slate-400">
              Sign-in is not configured yet. Contact the administrator when
              authentication is enabled.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}