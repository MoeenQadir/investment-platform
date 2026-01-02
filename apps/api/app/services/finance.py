import yfinance as yf
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
import numpy as np

def compute_provider_symbol(ticker_symbol: str, marketplace: str, exchange: str) -> str:
    """Compute provider_symbol from ticker, marketplace, and exchange.
    
    Rules:
    - US: provider_symbol = ticker_symbol
    - IN future: NSE => ticker.NS, BSE => ticker.BO
    """
    if marketplace == "US":
        return ticker_symbol
    elif marketplace == "IN":
        if exchange == "NSE":
            return f"{ticker_symbol}.NS"
        elif exchange == "BSE":
            return f"{ticker_symbol}.BO"
        else:
            return ticker_symbol
    else:
        return ticker_symbol

def fetch_stock_data(provider_symbol: str, start_date: date, end_date: Optional[date] = None) -> Optional[pd.DataFrame]:
    """Fetch stock price data from yfinance."""
    try:
        ticker = yf.Ticker(provider_symbol)
        end = end_date or datetime.now().date()
        hist = ticker.history(start=start_date, end=end + timedelta(days=1))
        if hist.empty:
            return None
        return hist
    except Exception:
        return None

def compute_returns(prices: pd.Series) -> pd.Series:
    """Compute daily returns from price series."""
    return prices.pct_change().dropna()

def compute_volatility(returns: pd.Series, window: int = 60) -> float:
    """Compute annualized volatility from returns."""
    if len(returns) < window:
        return np.nan
    recent_returns = returns.tail(window)
    return recent_returns.std() * np.sqrt(252)  # Annualized

def detect_price_move(provider_symbol: str, threshold_sigma: float = 2.0, lookback_days: int = 60) -> Optional[Dict]:
    """Detect if today's return exceeds threshold_sigma * volatility.
    
    Returns dict with 'triggered', 'current_return', 'volatility', 'sigma_move' if triggered.
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=lookback_days + 30)  # Extra buffer
        
        ticker = yf.Ticker(provider_symbol)
        hist = ticker.history(start=start_date, end=end_date + timedelta(days=1))
        
        if len(hist) < 2:
            return None
        
        prices = hist['Close']
        returns = compute_returns(prices)
        
        if len(returns) < lookback_days:
            return None
        
        recent_returns = returns.tail(lookback_days)
        volatility = recent_returns.std()
        
        # Today's return (most recent)
        current_return = returns.iloc[-1]
        sigma_move = abs(current_return) / volatility if volatility > 0 else 0
        
        triggered = abs(current_return) >= threshold_sigma * volatility
        
        return {
            'triggered': triggered,
            'current_return': float(current_return),
            'volatility': float(volatility),
            'sigma_move': float(sigma_move),
            'date': end_date.isoformat()
        }
    except Exception:
        return None

