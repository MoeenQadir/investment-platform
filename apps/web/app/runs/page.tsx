'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth'
import { runsApi, ResearchRun } from '@/lib/api'
import Link from 'next/link'

const statusBadge = (status: string) =>
  `badge ${
    status === 'COMPLETED' ? 'bg-emerald-400/10 text-emerald-300' :
    status === 'COMPLETED_WITH_WARNINGS' ? 'bg-amber-400/10 text-amber-300' :
    status === 'RUNNING' ? 'bg-sky-400/10 text-sky-300' :
    status === 'FAILED' ? 'bg-rose-400/10 text-rose-300' :
    'bg-slate-400/10 text-slate-300'
  }`

export default function RunsPage() {
  const { isSignedIn } = useAuth()
  const [runs, setRuns] = useState<ResearchRun[]>([])
  const [filterType, setFilterType] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')

  useEffect(() => {
    if (isSignedIn) loadRuns()
  }, [isSignedIn, filterType, filterStatus])

  const loadRuns = async () => {
    if (!isSignedIn) return
    try {
      const params: any = {}
      if (filterType) params.type = filterType
      if (filterStatus) params.status = filterStatus
      const res = await runsApi.list(params)
      setRuns(res.data)
    } catch (error) {
      console.error('Error loading runs:', error)
    }
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold text-white">Research Runs</h1>
        <p className="mt-1 text-sm text-slate-400">
          All research and explanation runs across your portfolios
        </p>

        <div className="glass-card p-6 mt-6">
          <div className="mb-4 flex gap-4">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="select w-44"
            >
              <option value="">All Types</option>
              <option value="RESEARCH">Research</option>
              <option value="EXPLAIN">Explain</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="select w-56"
            >
              <option value="">All Statuses</option>
              <option value="QUEUED">Queued</option>
              <option value="RUNNING">Running</option>
              <option value="COMPLETED">Completed</option>
              <option value="COMPLETED_WITH_WARNINGS">Completed with Warnings</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          <div className="space-y-2">
            {runs.map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`}>
                <div className="group rounded-xl border border-white/10 p-4 transition-colors hover:border-emerald-400/30 hover:bg-white/[0.03]">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-white">{run.run_type}</span>
                      {run.trigger_type && (
                        <span className="text-sm text-slate-500">({run.trigger_type})</span>
                      )}
                      <span className="text-sm text-slate-500">Portfolio #{run.portfolio_id}</span>
                    </div>
                    <span className={statusBadge(run.status)}>{run.status}</span>
                  </div>
                  <div className="text-sm text-slate-500 mt-1">
                    Created: {new Date(run.created_at).toLocaleString()}
                  </div>
                </div>
              </Link>
            ))}
            {runs.length === 0 && (
              <p className="py-8 text-center text-sm text-slate-500">
                No runs match the current filters.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}