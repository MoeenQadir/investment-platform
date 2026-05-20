import os
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd


class AlpacaProvider:
    name = "alpaca"

    def __init__(self) -> None:
        self.api_key = os.getenv("ALPACA_API_KEY", "")
        self.api_secret = os.getenv("ALPACA_API_SECRET", "")
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key or not self.api_secret:
            raise RuntimeError(
                "ALPACA_API_KEY / ALPACA_API_SECRET not set in environment"
            )
        from alpaca.data.historical import StockHistoricalDataClient

        self._client = StockHistoricalDataClient(self.api_key, self.api_secret)
        return self._client

    def fetch_stock_data(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> Optional[pd.DataFrame]:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        try:
            client = self._get_client()
            end = end_date or datetime.now().date()
            req = StockBarsRequest(
                symbol_or_symbols=provider_symbol,
                timeframe=TimeFrame.Day,
                start=datetime.combine(start_date, datetime.min.time()),
                end=datetime.combine(end, datetime.max.time()),
            )
            bars = client.get_stock_bars(req)
            df = bars.df
            if df is None or df.empty:
                return None
            if isinstance(df.index, pd.MultiIndex):
                df = df.xs(provider_symbol, level=0)
            df = df.rename(
                columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
            return df
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
        from alpaca.data.requests import StockLatestTradeRequest

        try:
            client = self._get_client()
            req = StockLatestTradeRequest(symbol_or_symbols=provider_symbol)
            trades = client.get_stock_latest_trade(req)
            trade = trades.get(provider_symbol)
            if trade is None:
                return None
            return float(trade.price)
        except Exception:
            return None

    def get_sector(self, provider_symbol: str) -> Optional[str]:
        # Alpaca free tier does not expose sector/fundamentals.
        return None
