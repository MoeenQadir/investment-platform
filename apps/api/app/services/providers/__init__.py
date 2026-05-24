import os
from functools import lru_cache

from .base import MarketDataProvider
from .yfinance_provider import YFinanceProvider


@lru_cache(maxsize=1)
def get_provider() -> MarketDataProvider:
    name = os.getenv("MARKET_DATA_PROVIDER", "yfinance").lower()
    if name == "alpaca":
        from .alpaca_provider import AlpacaProvider

        return AlpacaProvider()
    return YFinanceProvider()


__all__ = ["MarketDataProvider", "get_provider"]
