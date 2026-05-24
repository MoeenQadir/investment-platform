'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@clerk/nextjs'
import { portfolioApi, Portfolio, Holding } from '@/lib/api'

export default function PortfolioPage() {
  const { isSignedIn } = useAuth()
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedPortfolio, setSelectedPortfolio] = useState<Portfolio | null>(null)
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [newPortfolioName, setNewPortfolioName] = useState('')
  const [showAddHolding, setShowAddHolding] = useState(false)
  const [newHolding, setNewHolding] = useState({
    ticker_symbol: '',
    marketplace: 'US',
    exchange: 'NASDAQ',
    quantity: 0,
    buy_date: '',
    buy_price: 0,
    broker: '',
    currency: 'USD'
  })

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
      setNewHolding({
        ticker_symbol: '',
        marketplace: 'US',
        exchange: 'NASDAQ',
        quantity: 0,
        buy_date: '',
        buy_price: 0,
        broker: '',
        currency: 'USD'
      })
      setShowAddHolding(false)
      loadPortfolio(selectedPortfolio.id)
    } catch (error) {
      console.error('Error adding holding:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Portfolio Management</h1>
        
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Create Portfolio</h2>
          <div className="flex gap-4">
            <input
              type="text"
              value={newPortfolioName}
              onChange={(e) => setNewPortfolioName(e.target.value)}
              placeholder="Portfolio name"
              className="flex-1 border rounded px-4 py-2"
            />
            <button
              onClick={createPortfolio}
              className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
            >
              Create
            </button>
          </div>
        </div>

        {selectedPortfolio && (
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">{selectedPortfolio.name}</h2>
              <button
                onClick={() => setShowAddHolding(!showAddHolding)}
                className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
              >
                {showAddHolding ? 'Cancel' : 'Add Holding'}
              </button>
            </div>

            {showAddHolding && (
              <div className="bg-gray-50 p-4 rounded mb-4">
                <div className="grid grid-cols-2 gap-4">
                  <input
                    type="text"
                    placeholder="Ticker Symbol"
                    value={newHolding.ticker_symbol}
                    onChange={(e) => setNewHolding({...newHolding, ticker_symbol: e.target.value})}
                    className="border rounded px-3 py-2"
                  />
                  <select
                    value={newHolding.marketplace}
                    onChange={(e) => setNewHolding({...newHolding, marketplace: e.target.value})}
                    className="border rounded px-3 py-2"
                  >
                    <option value="US">US</option>
                  </select>
                  <select
                    value={newHolding.exchange}
                    onChange={(e) => setNewHolding({...newHolding, exchange: e.target.value})}
                    className="border rounded px-3 py-2"
                  >
                    <option value="NASDAQ">NASDAQ</option>
                    <option value="NYSE">NYSE</option>
                  </select>
                  <input
                    type="number"
                    placeholder="Quantity"
                    value={newHolding.quantity}
                    onChange={(e) => setNewHolding({...newHolding, quantity: parseFloat(e.target.value)})}
                    className="border rounded px-3 py-2"
                  />
                  <input
                    type="date"
                    value={newHolding.buy_date}
                    onChange={(e) => setNewHolding({...newHolding, buy_date: e.target.value})}
                    className="border rounded px-3 py-2"
                  />
                  <input
                    type="number"
                    placeholder="Buy Price"
                    value={newHolding.buy_price}
                    onChange={(e) => setNewHolding({...newHolding, buy_price: parseFloat(e.target.value)})}
                    className="border rounded px-3 py-2"
                  />
                </div>
                <button
                  onClick={addHolding}
                  className="mt-4 bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
                >
                  Add
                </button>
              </div>
            )}

            <table className="w-full mt-4">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">Ticker</th>
                  <th className="text-left p-2">Marketplace</th>
                  <th className="text-left p-2">Exchange</th>
                  <th className="text-left p-2">Quantity</th>
                  <th className="text-left p-2">Buy Date</th>
                  <th className="text-left p-2">Buy Price</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((holding) => (
                  <tr key={holding.id} className="border-b">
                    <td className="p-2">{holding.ticker_symbol}</td>
                    <td className="p-2">{holding.marketplace}</td>
                    <td className="p-2">{holding.exchange}</td>
                    <td className="p-2">{holding.quantity}</td>
                    <td className="p-2">{holding.buy_date}</td>
                    <td className="p-2">${holding.buy_price.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

