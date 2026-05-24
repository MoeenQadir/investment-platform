'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@clerk/nextjs'
import { runsApi, portfolioApi, researchApi, ResearchRun, Portfolio } from '@/lib/api'
import Link from 'next/link'
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'

export default function DashboardPage() {
  const { isSignedIn } = useAuth()
  const [runs, setRuns] = useState<ResearchRun[]>([])
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null)

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
      await researchApi.run(selectedPortfolioId)
      setTimeout(loadRuns, 1000)
    } catch (error) {
      console.error('Error triggering research:', error)
    }
  }

  // Process sector exposure data from latest completed run
  const latestRun = runs.find(r => r.status === 'COMPLETED' && r.metrics_json?.sector_exposure)
  const sectorData = latestRun?.metrics_json?.sector_exposure
    ? Object.entries(latestRun.metrics_json.sector_exposure).map(([name, value]: [string, any]) => ({
        name,
        value: (value * 100).toFixed(1)
      }))
    : []

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d']

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <button
            onClick={triggerResearch}
            className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
          >
            Run Deep Research
          </button>
        </div>

        {sectorData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Sector Exposure</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={sectorData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name}: ${value}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {sectorData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Latest Runs</h2>
          <div className="space-y-2">
            {runs.slice(0, 10).map((run) => (
              <Link key={run.id} href={`/runs/${run.id}`}>
                <div className="border rounded p-4 hover:bg-gray-50 cursor-pointer">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="font-medium">{run.run_type}</span>
                      {run.trigger_type && (
                        <span className="ml-2 text-gray-500">({run.trigger_type})</span>
                      )}
                    </div>
                    <span className={`px-3 py-1 rounded text-sm ${
                      run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      run.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
                      run.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {run.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {new Date(run.created_at).toLocaleString()}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

