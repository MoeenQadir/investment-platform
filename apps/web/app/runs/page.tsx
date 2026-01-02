'use client'

import { useState, useEffect } from 'react'
import { runsApi, ResearchRun } from '@/lib/api'
import Link from 'next/link'

export default function RunsPage() {
  const [runs, setRuns] = useState<ResearchRun[]>([])
  const [filterType, setFilterType] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')

  useEffect(() => {
    loadRuns()
  }, [filterType, filterStatus])

  const loadRuns = async () => {
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
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Research Runs</h1>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex gap-4 mb-4">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="border rounded px-4 py-2"
            >
              <option value="">All Types</option>
              <option value="RESEARCH">Research</option>
              <option value="EXPLAIN">Explain</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="border rounded px-4 py-2"
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
                <div className="border rounded p-4 hover:bg-gray-50 cursor-pointer">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="font-medium">{run.run_type}</span>
                      {run.trigger_type && (
                        <span className="ml-2 text-gray-500">({run.trigger_type})</span>
                      )}
                      <span className="ml-4 text-sm text-gray-500">Portfolio #{run.portfolio_id}</span>
                    </div>
                    <span className={`px-3 py-1 rounded text-sm ${
                      run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                      run.status === 'COMPLETED_WITH_WARNINGS' ? 'bg-yellow-100 text-yellow-800' :
                      run.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
                      run.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {run.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    Created: {new Date(run.created_at).toLocaleString()}
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

