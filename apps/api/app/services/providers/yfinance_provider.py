from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf


class YFinanceProvider:
    name = "yfinance"

    def fetch_stock_data(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> Optional[pd.DataFrame]:
        try:
            ticker = yf.Ticker(provider_symbol)
            end = end_date or datetime.now().date()
            hist = ticker.history(start=start_date, end=end + timedelta(days=1))
            if hist.empty:
                return None
            return hist
        except Exception:
            return None

    def fetch_recent_closes(
        self,
        provider_symbol: str,
        lookback_days: int,
    ) -> Optional[pd.Series]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=lookback_days + 30)
        hist = self.fetch_stock_data(provider_symbol, start_date, end_date)
        if hist is None or len(hist) < 2:
            return None
        return hist["Close"]

    def get_latest_price(self, provider_symbol: str) -> Optional[float]:
        try:
            ticker = yf.Ticker(provider_symbol)
            hist = ticker.history(period="1d")
            if hist.empty:
                return None
            return float(hist["Close"].iloc[-1])
        except Exception:
            return None

    def get_sector(self, provider_symbol: str) -> Optional[str]:
        try:
            ticker = yf.Ticker(provider_symbol)
            info = ticker.info
            sector = info.get("sector", "") if isinstance(info, dict) else ""
            return sector or None
        except Exception:
            return None
