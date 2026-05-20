from typing import Dict, Optional
from datetime import datetime, date

import numpy as np
import pandas as pd

from .providers import get_provider


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


def fetch_stock_data(
    provider_symbol: str,
    start_date: date,
    end_date: Optional[date] = None,
) -> Optional[pd.DataFrame]:
    """Fetch stock price data via the configured market data provider."""
    return get_provider().fetch_stock_data(provider_symbol, start_date, end_date)


def compute_returns(prices: pd.Series) -> pd.Series:
    """Compute daily returns from price series."""
    return prices.pct_change().dropna()


def compute_volatility(returns: pd.Series, window: int = 60) -> float:
    """Compute annualized volatility from returns."""
    if len(returns) < window:
        return np.nan
    recent_returns = returns.tail(window)
    return recent_returns.std() * np.sqrt(252)


def detect_price_move(
    provider_symbol: str,
    threshold_sigma: float = 2.0,
    lookback_days: int = 60,
) -> Optional[Dict]:
    """Detect if today's return exceeds threshold_sigma * volatility."""
    try:
        prices = get_provider().fetch_recent_closes(provider_symbol, lookback_days)
        if prices is None:
            return None

        returns = compute_returns(prices)
        if len(returns) < lookback_days:
            return None

        recent_returns = returns.tail(lookback_days)
        volatility = recent_returns.std()

        current_return = returns.iloc[-1]
        sigma_move = abs(current_return) / volatility if volatility > 0 else 0
        triggered = abs(current_return) >= threshold_sigma * volatility

        return {
            "triggered": triggered,
            "current_return": float(current_return),
            "volatility": float(volatility),
            "sigma_move": float(sigma_move),
            "date": datetime.now().date().isoformat(),
        }
    except Exception:
        return None
