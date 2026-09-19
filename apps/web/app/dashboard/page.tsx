'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth'
import { runsApi, portfolioApi, researchApi, ResearchRun, Portfolio } from '@/lib/api'
import Link from 'next/link'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#10b981', '#14b8a6', '#f5b942', '#38bdf8', '#a78bfa', '#f472b6']

export default function DashboardPage() {
  const { isSignedIn } = useAuth()
  const [runs, setRuns] = useState<ResearchRun[]>([])
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null)
  const [triggering, setTriggering] = useState(false)

  useEffect(() => {
    if (!isSignedIn) return
    portfolioApi.list().then(res => {
      setPortfolios(res.data)
      if (res.data.length > 0) setSelectedPortfolioId(res.data[0].id)
    }).catch(console.error)
  }, [isSignedIn])

  useEffect(() => {
    if (selectedPortfolioId) loadRuns()
  }, [selectedPortfolioId])

  const loadRuns = async () => {
    if (!selectedPortfolioId) return
    try {
      const res = await runsApi.list({ portfolio_id: selectedPortfolioId })
      setRuns(res.data)
    } catch (error) {
      console.error('Error loading runs:', error)
    }
  }

  const triggerResearch = async () => {
    if (!selectedPortfolioId) return
    try {
      setTriggering(true)
      await researchApi.run(selectedPortfolioId)
      setTimeout(() => { loadRuns(); setTriggering(false) }, 1200)
    } catch (error) {
      console.error('Error triggering research:', error)
      setTriggering(false)
    }
  }

  const latestRun = runs.find(r => r.status === 'COMPLETED' && r.metrics_json?.sector_exposure)
  const sectorData = latestRun?.metrics_json?.sector_exposure
    ? Object.entries(latestRun.metrics_json.sector_exposure).map(([name, value]: [string, any]) => ({
        name,
        value: (value * 100).toFixed(1)
      }))
    : []

  const statusBadge = (status: string) =>
    `badge ${
      status === 'COMPLETED' ? 'bg-emerald-400/10 text-emerald-300' :
      status === 'COMPLETED_WITH_WARNINGS' ? 'bg-amber-400/10 text-amber-300' :
      status === 'RUNNING' ? 'bg-sky-400/10 text-sky-300' :
      status === 'FAILED' ? 'bg-rose-400/10 text-rose-300' :
      'bg-slate-400/10 text-slate-300'
    }`

  return (
    <div className="py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Dashboard</h1>
            <p className="mt-1 text-sm text-slate-400">
              Overview of your research runs and sector exposure
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedPortfolioId ?? ''}
              onChange={(e) => setSelectedPortfolioId(Number(e.target.value))}
              className="select w-56"
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button
              onClick={triggerResearch}
              disabled={!selectedPortfolioId || triggering}
              className="btn-accent disabled:cursor-not-allowed disabled:opacity-60"
            >
              {triggering ? 'Triggering…' : 'Run Deep Research'}
            </button>
          </div>
        </div>

        {sectorData.length > 0 && (
          <div className="glass-card p-6 mb-6">
            <h2 className="text-xl font-semibold text-white mb-4">Sector Exposure</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sectorData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={90}
                  fill="#10b981"
                  dataKey="value"
                >
                  {sectorData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="glass-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Latest Runs</h2>
            <Link href="/runs" className="text-sm font-medium text-emerald-300 hover:text-emerald-200">
              View all →
            </Link>
          </div>
          <div className="space-y-2">
            {runs.slice(0, 10).map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`}>
                <div className="group rounded-xl border border-white/10 p-4 transition-colors hover:border-emerald-400/30 hover:bg-white/[0.03]">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-white">{run.run_type}</span>
                      {run.trigger_type && (
                        <span className="text-sm text-slate-500">({run.trigger_type})</span>
                      )}
                    </div>
                    <span className={statusBadge(run.status)}>{run.status}</span>
                  </div>
                  <div className="text-sm text-slate-500 mt-1">
                    {new Date(run.created_at).toLocaleString()}
                  </div>
                </div>
              </Link>
            ))}
            {runs.length === 0 && (
              <p className="py-8 text-center text-sm text-slate-500">
                No research runs yet — select a portfolio and hit “Run Deep Research”.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}