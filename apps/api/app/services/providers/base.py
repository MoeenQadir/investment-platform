from typing import Optional, Protocol
from datetime import date
import pandas as pd


class MarketDataProvider(Protocol):
    name: str

    def fetch_stock_data(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> Optional[pd.DataFrame]:
        ...

    def fetch_recent_closes(
        self,
        provider_symbol: str,
        lookback_days: int,
    ) -> Optional[pd.Series]:
        ...

    def get_latest_price(self, provider_symbol: str) -> Optional[float]:
        ...

    def get_sector(self, provider_symbol: str) -> Optional[str]:
        """Return provider-reported sector name, or None if unavailable."""
        ...
