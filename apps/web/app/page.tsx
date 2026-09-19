import Link from 'next/link'
import { brand } from '@/lib/brand'

const features = [
  {
    title: 'Deep Research Runs',
    body: 'Trigger automated deep-research workflows that pull live market data, SEC filings and insider activity for every holding.',
  },
  {
    title: 'Explainable Insights',
    body: 'Every conclusion is explained with quantified driver scores — market, sector, filings, insider and technical — never a black box.',
  },
  {
    title: 'Sector Exposure Maps',
    body: 'Normalized sector breakdowns with ETF proxy tracking to see exactly where your portfolio is positioned.',
  },
  {
    title: 'Price-Move Detection',
    body: '2σ volatility alerts that explain why a stock moved and whether it matters for your thesis.',
  },
  {
    title: 'Full Run History',
    body: 'Every run stores a holdings snapshot for reproducibility, with filtering by type and status.',
  },
  {
    title: 'Free-Text Explanations',
    body: 'Ask the platform to explain a move or trigger and receive a structured, narrative report with sources.',
  },
]

const drivers = [
  { name: 'Market', detail: 'SPY correlation & alignment' },
  { name: 'Sector', detail: 'ETF proxy correlation' },
  { name: 'Filings', detail: 'SEC filing recency (3/7/14d)' },
  { name: 'Insider', detail: 'Insider activity recency' },
  { name: 'Technical', detail: 'Price move vs. 2σ volatility' },
]

export default function Home() {
  return (
    <div className="relative overflow-hidden">
      <section className="mx-auto max-w-7xl px-4 pb-20 pt-20 text-center sm:px-6 lg:px-8">
        <span className="glass badge mb-6 text-emerald-300">
          AI-powered · Data-driven · Reproducible
        </span>
        <h1 className="mx-auto max-w-4xl text-4xl font-bold leading-[1.1] text-white sm:text-6xl">
          Investment research that <span className="gradient-text">explains itself</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-400">
          {brand.tagline}. From live market data and SEC filings to insider
          trading and driver scoring — then a clear narrative on why it
          matters.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link href="/portfolio" className="btn-accent">
            Get started
          </Link>
          <Link href="/dashboard" className="btn-ghost">
            View dashboard
          </Link>
        </div>

        <div className="mx-auto mt-16 grid max-w-3xl grid-cols-2 gap-6 sm:grid-cols-4">
          {[
            ['3–5', 'Drivers per run'],
            ['2σ', 'Moves flagged'],
            ['SEC / EDGAR', 'Filings tracked'],
            ['100%', 'Reproducible'],
          ].map(([value, label]) => (
            <div key={label} className="glass-card p-5">
              <p className="gradient-text text-2xl font-bold">{value}</p>
              <p className="mt-1 text-xs uppercase tracking-wider text-slate-400">
                {label}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-white/10 bg-ink-900/40 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-center text-3xl font-bold text-white sm:text-4xl">
            Everything you need to <span className="gradient-text">research with clarity</span>
          </h2>
          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <div key={feature.title} className="glass-card p-6 transition-colors hover:border-emerald-400/30">
                <h3 className="text-lg font-semibold text-white">{feature.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">
                  {feature.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid items-center gap-12 lg:grid-cols-2">
            <div>
              <h2 className="text-3xl font-bold text-white sm:text-4xl">
                Quantified driver scoring, <span className="gradient-text">not guesswork</span>
              </h2>
              <p className="mt-5 leading-relaxed text-slate-400">
                Each research run scores five independent drivers from live data
                and picks the strongest signals — then n8n orchestrates a
                narrative report around those numbers, not the other way
                around.
              </p>
              <Link href="/portfolio" className="btn-accent mt-8">
                Start a research run
              </Link>
            </div>
            <ul className="space-y-3">
              {drivers.map((driver) => (
                <li key={driver.name} className="glass-card flex items-center justify-between p-5">
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-400/10 text-sm font-bold text-emerald-300">
                    {driver.name[0]}
                  </span>
                  <span className="flex-1 px-4 font-semibold text-white">{driver.name}</span>
                  <span className="text-right text-xs text-slate-400">{driver.detail}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 bg-gradient-to-b from-ink-900/60 to-ink-950 py-20">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-white sm:text-4xl">
            Ready to see your portfolio in a new light?
          </h2>
          <p className="mt-5 text-slate-400">
            Create a portfolio, add your holdings and press one button to get a
            complete, explained research report.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <Link href="/portfolio" className="btn-accent">
              Create portfolio
            </Link>
            <a href={`mailto:${brand.email}`} className="btn-ghost">
              Contact support
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}