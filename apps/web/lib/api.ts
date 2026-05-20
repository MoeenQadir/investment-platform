import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token getter — wire from a Clerk-aware hook in components (e.g. useAuth().getToken).
// On the server side, pass a token explicitly via setAuthToken.
let _tokenGetter: (() => Promise<string | null>) | null = null

export function setAuthTokenGetter(fn: () => Promise<string | null>): void {
  _tokenGetter = fn
}

export function setAuthToken(token: string | null): void {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

api.interceptors.request.use(async (config) => {
  if (_tokenGetter && !config.headers.Authorization) {
    const token = await _tokenGetter()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

export interface Portfolio {
  id: number
  name: string
  user_id: number
}

export interface Holding {
  id: number
  ticker_symbol: string
  marketplace: string
  exchange: string
  provider_symbol: string
  quantity: number
  buy_date: string
  buy_price: number
  broker?: string
  currency?: string
}

export interface ResearchRun {
  id: string
  run_type: 'RESEARCH' | 'EXPLAIN'
  trigger_type?: 'PRICE_MOVE' | 'FILING_EVENT' | 'SCHEDULED'
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'COMPLETED_WITH_WARNINGS' | 'FAILED'
  portfolio_id: number
  created_at: string
  updated_at: string
  params_json?: any
  holdings_snapshot_json?: any
  warnings_json?: any
  metrics_json?: any
  report_md?: string
  sources?: Array<{ id: number; title: string; url: string; retrieved_at: string }>
}

export const portfolioApi = {
  create: (name: string) => api.post<Portfolio>('/api/portfolio', { name }),
  get: (id: number) => api.get<Portfolio>(`/api/portfolio/${id}`),
  listHoldings: (id: number) => api.get<Holding[]>(`/api/portfolio/${id}/holdings`),
  upsertHoldings: (id: number, holdings: Omit<Holding, 'id' | 'provider_symbol'>[]) =>
    api.post<Holding[]>(`/api/portfolio/${id}/holdings`, holdings),
}

export const researchApi = {
  run: (portfolio_id: number, preferences: any = {}, strategy: string = 'default') =>
    api.post<{ run_id: string; status: string }>('/api/research/run', {
      portfolio_id,
      preferences,
      strategy,
    }),
}

export const explainApi = {
  run: (portfolio_id: number, trigger_type: string, trigger_payload: any = {}) =>
    api.post<{ run_id: string; status: string }>('/api/explain/run', {
      portfolio_id,
      trigger_type,
      trigger_payload,
    }),
}

export const runsApi = {
  list: (params?: { type?: string; status?: string; portfolio_id?: number }) =>
    api.get<ResearchRun[]>('/api/runs', { params }),
  get: (runId: string) => api.get<ResearchRun>(`/api/runs/${runId}`),
}

