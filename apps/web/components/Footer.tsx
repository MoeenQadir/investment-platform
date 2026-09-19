import Link from 'next/link'
import { brand } from '@/lib/brand'

export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-ink-950">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 md:grid-cols-3">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 text-sm font-black text-ink-950">
                A
              </span>
              <div>
                <p className="text-sm font-bold text-white">{brand.name}</p>
                <p className="text-[10px] uppercase tracking-widest text-emerald-300/80">
                  Research Platform
                </p>
              </div>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-slate-400">
              {brand.tagline}. Built on live market data, SEC filings, insider
              activity and quantitative driver scoring.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-300">
              Platform
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm">
              {brand.nav.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-slate-400 transition-colors hover:text-emerald-300"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold uppercase tracking-widest text-slate-300">
              Contact
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm text-slate-400">
              <li>
                <a
                  href={`mailto:${brand.email}`}
                  className="transition-colors hover:text-emerald-300"
                >
                  {brand.email}
                </a>
              </li>
              <li>
                <a
                  href={`tel:${brand.phone}`}
                  className="transition-colors hover:text-emerald-300"
                >
                  {brand.phoneDisplay}
                </a>
              </li>
              <li>{brand.location}</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-3 border-t border-white/10 pt-6 text-xs text-slate-500 sm:flex-row">
          <p>
            © {new Date().getFullYear()} {brand.name}. All rights reserved.
          </p>
          <p>
            {brand.email} · {brand.phoneDisplay} · {brand.location}
          </p>
        </div>
      </div>
    </footer>
  )
}