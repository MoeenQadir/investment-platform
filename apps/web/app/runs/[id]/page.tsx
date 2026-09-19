'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { runsApi, ResearchRun } from '@/lib/api'

const statusBadge = (status: string) =>
  `badge ${
    status === 'COMPLETED' ? 'bg-emerald-400/10 text-emerald-300' :
    status === 'COMPLETED_WITH_WARNINGS' ? 'bg-amber-400/10 text-amber-300' :
    status === 'RUNNING' ? 'bg-sky-400/10 text-sky-300' :
    status === 'FAILED' ? 'bg-rose-400/10 text-rose-300' :
    'bg-slate-400/10 text-slate-300'
  }`

export default function RunDetailPage() {
  const { isSignedIn } = useAuth()
  const params = useParams()
  const runId = params.id as string
  const [run, setRun] = useState<ResearchRun | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isSignedIn) return
    loadRun()
    const interval = setInterval(() => {
      if (run?.status === 'RUNNING' || run?.status === 'QUEUED') {
        loadRun()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [isSignedIn, runId, run?.status])

  const loadRun = async () => {
    if (!isSignedIn) return
    try {
      const res = await runsApi.get(runId)
      setRun(res.data)
      setLoading(false)
    } catch (error) {
      console.error('Error loading run:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center py-8">
        <div className="flex items-center gap-3 text-slate-400">
          <span className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-400/30 border-t-emerald-400" />
          Loading run details…
        </div>
      </div>
    )
  }

  if (!run) {
    return (
      <div className="py-8">
        <div className="glass-card mx-auto max-w-2xl p-10 text-center">
          <h1 className="text-2xl font-bold text-white">Run not found</h1>
          <p className="mt-2 text-sm text-slate-400">
            This run may have been deleted or you do not have access to it.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-6 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
            <div>
              <h1 className="text-3xl font-bold text-white">{run.run_type}</h1>
              {run.trigger_type && (
                <p className="mt-1 text-slate-400">Trigger: {run.trigger_type}</p>
              )}
            </div>
            <span className={statusBadge(run.status)}>{run.status}</span>
          </div>

          {run.warnings_json && Object.keys(run.warnings_json).length > 0 && (
            <div className="mb-4 rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
              <h3 className="font-semibold text-amber-300 mb-2">Warnings</h3>
              <pre className="whitespace-pre-wrap text-sm text-amber-200/90">
                {JSON.stringify(run.warnings_json, null, 2)}
              </pre>
            </div>
          )}

          {run.metrics_json && (
            <div className="mb-4">
              <h3 className="mb-2 font-semibold text-white">Metrics</h3>
              <pre className="overflow-auto rounded-xl border border-white/10 bg-ink-950/60 p-4 text-sm text-slate-300">
                {JSON.stringify(run.metrics_json, null, 2)}
              </pre>
            </div>
          )}

          {run.report_md && (
            <div className="mb-4">
              <h3 className="mb-2 font-semibold text-white">Report</h3>
              <div className="rounded-xl border border-white/10 bg-ink-950/60 p-4">
                <pre className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
                  {run.report_md}
                </pre>
              </div>
            </div>
          )}

          {run.sources && run.sources.length > 0 && (
            <div>
              <h3 className="mb-2 font-semibold text-white">Sources</h3>
              <ul className="space-y-2">
                {run.sources.map((source) => (
                  <li key={source.id}>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-300 hover:underline"
                    >
                      {source.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}