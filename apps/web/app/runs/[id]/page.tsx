'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { runsApi, ResearchRun } from '@/lib/api'

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
    return <div className="p-8">Loading...</div>
  }

  if (!run) {
    return <div className="p-8">Run not found</div>
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Run Details</h1>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-semibold">{run.run_type}</h2>
              {run.trigger_type && (
                <p className="text-gray-500">Trigger: {run.trigger_type}</p>
              )}
            </div>
            <span className={`px-4 py-2 rounded text-sm font-medium ${
              run.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
              run.status === 'COMPLETED_WITH_WARNINGS' ? 'bg-yellow-100 text-yellow-800' :
              run.status === 'RUNNING' ? 'bg-blue-100 text-blue-800' :
              run.status === 'FAILED' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {run.status}
            </span>
          </div>

          {run.warnings_json && Object.keys(run.warnings_json).length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-4 mb-4">
              <h3 className="font-semibold text-yellow-800 mb-2">Warnings</h3>
              <pre className="text-sm text-yellow-700 whitespace-pre-wrap">
                {JSON.stringify(run.warnings_json, null, 2)}
              </pre>
            </div>
          )}

          {run.metrics_json && (
            <div className="mb-4">
              <h3 className="font-semibold mb-2">Metrics</h3>
              <pre className="bg-gray-50 p-4 rounded text-sm overflow-auto">
                {JSON.stringify(run.metrics_json, null, 2)}
              </pre>
            </div>
          )}

          {run.report_md && (
            <div className="mb-4">
              <h3 className="font-semibold mb-2">Report</h3>
              <div className="bg-gray-50 p-4 rounded prose max-w-none">
                <pre className="whitespace-pre-wrap text-sm">
                  {run.report_md}
                </pre>
              </div>
            </div>
          )}

          {run.sources && run.sources.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2">Sources</h3>
              <ul className="space-y-2">
                {run.sources.map((source) => (
                  <li key={source.id}>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:underline"
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

