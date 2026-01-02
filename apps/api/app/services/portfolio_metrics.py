from typing import Dict, List, Optional
from datetime import date
from sqlalchemy.orm import Session
import yfinance as yf
import pandas as pd
import numpy as np
from app.db.models import Holding, CanonicalSector
from app.services.finance import fetch_stock_data, compute_returns, compute_volatility
from app.services.sector import resolve_canonical_sector, resolve_sector_etf, get_market_etf

def compute_portfolio_metrics(
    db: Session,
    holdings: List[Holding],
    benchmark_etf: str = "SPY"
) -> Dict:
    """Compute portfolio-level metrics: exposure, performance, benchmarks.
    
    Returns dict with:
    - sector_exposure: {sector: weight}
    - market_cap_exposure: {bucket: weight} (v1 placeholder)
    - holdings_performance: [{holding_id, return_pct, volatility, etc}]
    - portfolio_total_return: float
    - benchmark_comparison: {benchmark_return, excess_return}
    """
    if not holdings:
        return {
            'sector_exposure': {},
            'market_cap_exposure': {},
            'holdings_performance': [],
            'portfolio_total_return': 0.0,
            'benchmark_comparison': {}
        }
    
    # Calculate total portfolio value
    total_value = 0.0
    holding_values = {}
    
    for holding in holdings:
        try:
            ticker = yf.Ticker(holding.provider_symbol)
            current_price = ticker.history(period="1d")['Close'].iloc[-1]
            value = current_price * holding.quantity
            holding_values[holding.id] = value
            total_value += value
        except Exception:
            # If we can't get price, use buy_price
            value = holding.buy_price * holding.quantity
            holding_values[holding.id] = value
            total_value += value
    
    # Sector exposure
    sector_weights = {}
    holdings_performance = []
    
    for holding in holdings:
        weight = holding_values.get(holding.id, 0) / total_value if total_value > 0 else 0
        
        # Get sector (v1: try yfinance, fallback to unknown)
        sector_name = "Unknown"
        try:
            ticker = yf.Ticker(holding.provider_symbol)
            info = ticker.info
            provider_sector = info.get('sector', '')
            if provider_sector:
                canonical = resolve_canonical_sector(db, "yfinance", provider_sector)
                if canonical:
                    sector_name = canonical.canonical_name
                else:
                    sector_name = provider_sector
        except Exception:
            pass
        
        sector_weights[sector_name] = sector_weights.get(sector_name, 0) + weight
        
        # Compute holding performance
        try:
            ticker = yf.Ticker(holding.provider_symbol)
            hist = ticker.history(start=holding.buy_date, end=date.today() + pd.Timedelta(days=1))
            if not hist.empty:
                buy_price = holding.buy_price
                current_price = hist['Close'].iloc[-1]
                return_pct = ((current_price - buy_price) / buy_price) * 100
                
                # Volatility
                returns = compute_returns(hist['Close'])
                vol = compute_volatility(returns) if len(returns) > 0 else 0.0
                
                holdings_performance.append({
                    'holding_id': holding.id,
                    'ticker_symbol': holding.ticker_symbol,
                    'return_pct': float(return_pct),
                    'volatility': float(vol),
                    'current_price': float(current_price),
                    'buy_price': float(buy_price),
                    'value': float(holding_values.get(holding.id, 0))
                })
        except Exception:
            holdings_performance.append({
                'holding_id': holding.id,
                'ticker_symbol': holding.ticker_symbol,
                'return_pct': 0.0,
                'volatility': 0.0,
                'current_price': holding.buy_price,
                'buy_price': holding.buy_price,
                'value': float(holding_values.get(holding.id, 0))
            })
    
    # Portfolio total return (weighted average)
    portfolio_return = sum(
        hp['return_pct'] * (holding_values.get(hp['holding_id'], 0) / total_value)
        for hp in holdings_performance
        if total_value > 0
    )
    
    # Benchmark comparison
    try:
        benchmark_ticker = yf.Ticker(benchmark_etf)
        # Use same period as average holding buy date
        avg_buy_date = pd.Timestamp(min(h.buy_date for h in holdings))
        bench_hist = benchmark_ticker.history(start=avg_buy_date, end=date.today() + pd.Timedelta(days=1))
        if not bench_hist.empty:
            bench_start = bench_hist['Close'].iloc[0]
            bench_end = bench_hist['Close'].iloc[-1]
            benchmark_return = ((bench_end - bench_start) / bench_start) * 100
            excess_return = portfolio_return - benchmark_return
        else:
            benchmark_return = 0.0
            excess_return = 0.0
    except Exception:
        benchmark_return = 0.0
        excess_return = 0.0
    
    return {
        'sector_exposure': sector_weights,
        'market_cap_exposure': {},  # v1 placeholder
        'holdings_performance': holdings_performance,
        'portfolio_total_return': float(portfolio_return),
        'benchmark_comparison': {
            'benchmark_return': float(benchmark_return),
            'excess_return': float(excess_return),
            'benchmark_etf': benchmark_etf
        }
    }

def detect_price_move_events_for_portfolio(
    db: Session,
    holdings: List[Holding],
    threshold_sigma: float = 2.0
) -> List[Dict]:
    """Detect price move events for all holdings in portfolio.
    
    Returns list of dicts with holding_id, provider_symbol, and move info.
    """
    from app.services.finance import detect_price_move
    
    events = []
    for holding in holdings:
        move_info = detect_price_move(holding.provider_symbol, threshold_sigma)
        if move_info and move_info.get('triggered'):
            events.append({
                'holding_id': holding.id,
                'provider_symbol': holding.provider_symbol,
                'ticker_symbol': holding.ticker_symbol,
                **move_info
            })
    return events

