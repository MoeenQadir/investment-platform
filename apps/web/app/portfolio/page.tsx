'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth'
import { portfolioApi, Portfolio, Holding } from '@/lib/api'

const emptyHolding = {
  ticker_symbol: '',
  marketplace: 'US',
  exchange: 'NASDAQ',
  quantity: 0,
  buy_date: '',
  buy_price: 0,
  broker: '',
  currency: 'USD'
}

export default function PortfolioPage() {
  const { isSignedIn } = useAuth()
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null)
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [newPortfolioName, setNewPortfolioName] = useState('')
  const [showAddHolding, setShowAddHolding] = useState(false)
  const [newHolding, setNewHolding] = useState(emptyHolding)

  useEffect(() => {
    if (isSignedIn) loadPortfolios()
  }, [isSignedIn])

  const loadPortfolios = async () => {
    try {
      const res = await portfolioApi.list()
      setPortfolios(res.data)
      if (res.data.length > 0) {
        loadPortfolio(res.data[0].id)
      }
    } catch (error) {
      console.error('Error loading portfolios:', error)
    }
  }

  const loadPortfolio = async (id: number) => {
    try {
      const portfolioRes = await portfolioApi.get(id)
      setSelectedPortfolio(portfolioRes.data)
      const holdingsRes = await portfolioApi.listHoldings(id)
      setHoldings(holdingsRes.data)
    } catch (error) {
      console.error('Error loading portfolio:', error)
    }
  }

  const createPortfolio = async () => {
    try {
      const res = await portfolioApi.create(newPortfolioName)
      setPortfolios([...portfolios, res.data])
      setNewPortfolioName('')
      loadPortfolio(res.data.id)
    } catch (error) {
      console.error('Error creating portfolio:', error)
    }
  }

  const addHolding = async () => {
    if (!selectedPortfolio) return
    try {
      await portfolioApi.upsertHoldings(selectedPortfolio.id, [newHolding as any])
      setNewHolding(emptyHolding)
      setShowAddHolding(false)
      loadPortfolio(selectedPortfolio.id)
    } catch (error) {
      console.error('Error adding holding:', error)
    }
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">Portfolio Management</h1>
            <p className="mt-1 text-sm text-slate-400">
              Create portfolios and add holdings for deep research
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedPortfolio?.id ?? ''}
              onChange={(e) => {
                const id = Number(e.target.value)
                const p = portfolios.find((x) => x.id === id)
                setSelectedPortfolio(p ?? null)
                if (p) loadPortfolio(p.id)
              }}
              className="select w-56"
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            {selectedPortfolio && (
              <button
                onClick={() => setShowAddHolding(!showAddHolding)}
                className="btn-accent"
              >
                {showAddHolding ? 'Cancel' : 'Add Holding'}
              </button>
            )}
          </div>
        </div>

        <div className="glass-card p-6 mb-6">
          <h2 className="text-xl font-semibold text-white mb-4">Create Portfolio</h2>
          <div className="flex gap-4">
            <input
              type="text"
              value={newPortfolioName}
              onChange={(e) => setNewPortfolioName(e.target.value)}
              placeholder="Portfolio name"
              className="input flex-1"
            />
            <button
              onClick={createPortfolio}
              className="btn-ghost"
            >
              Create
            </button>
          </div>
        </div>

        {selectedPortfolio && (
          <div className="glass-card p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{selectedPortfolio.name}</h2>

            {showAddHolding && (
              <div className="mb-6 rounded-xl border border-white/10 bg-ink-900/50 p-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <input
                    type="text"
                    placeholder="Ticker Symbol"
                    value={newHolding.ticker_symbol}
                    onChange={(e) => setNewHolding({...newHolding, ticker_symbol: e.target.value})}
                    className="input"
                  />
                  <select
                    value={newHolding.marketplace}
                    onChange={(e) => setNewHolding({...newHolding, marketplace: e.target.value})}
                    className="select"
                  >
                    <option value="US">US</option>
                  </select>
                  <select
                    value={newHolding.exchange}
                    onChange={(e) => setNewHolding({...newHolding, exchange: e.target.value})}
                    className="select"
                  >
                    <option value="NASDAQ">NASDAQ</option>
                    <option value="NYSE">NYSE</option>
                  </select>
                  <input
                    type="number"
                    placeholder="Quantity"
                    value={newHolding.quantity}
                    onChange={(e) => setNewHolding({...newHolding, quantity: parseFloat(e.target.value)})}
                    className="input"
                  />
                  <input
                    type="date"
                    value={newHolding.buy_date}
                    onChange={(e) => setNewHolding({...newHolding, buy_date: e.target.value})}
                    className="input"
                  />
                  <input
                    type="number"
                    placeholder="Buy Price"
                    value={newHolding.buy_price}
                    onChange={(e) => setNewHolding({...newHolding, buy_price: parseFloat(e.target.value)})}
                    className="input"
                  />
                </div>
                <button
                  onClick={addHolding}
                  className="btn-accent mt-5"
                >
                  Add holding
                </button>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wider text-slate-400">
                    <th className="p-2 font-medium">Ticker</th>
                    <th className="p-2 font-medium">Marketplace</th>
                    <th className="p-2 font-medium">Exchange</th>
                    <th className="p-2 font-medium">Quantity</th>
                    <th className="p-2 font-medium">Buy Date</th>
                    <th className="p-2 font-medium">Buy Price</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((holding) => (
                    <tr key={holding.id} className="border-b border-white/5 last:border-0">
                      <td className="p-2 font-semibold text-emerald-300">{holding.ticker_symbol}</td>
                      <td className="p-2 text-slate-300">{holding.marketplace}</td>
                      <td className="p-2 text-slate-300">{holding.exchange}</td>
                      <td className="p-2 text-slate-300">{holding.quantity}</td>
                      <td className="p-2 text-slate-300">{holding.buy_date}</td>
                      <td className="p-2 text-slate-300">${holding.buy_price.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {holdings.length === 0 && (
                <p className="py-8 text-center text-sm text-slate-500">
                  No holdings yet — add your first ticker to start researching.
                </p>
              )}
            </div>
          </div>
        )}

        {!selectedPortfolio && portfolios.length === 0 && (
          <div className="glass-card p-10 text-center">
            <p className="text-slate-400">
              No portfolios yet. Create your first one above to get started.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}