import pytest
from app.services.finance import compute_provider_symbol

def test_provider_symbol_us():
    assert compute_provider_symbol("AAPL", "US", "NASDAQ") == "AAPL"
    assert compute_provider_symbol("MSFT", "US", "NYSE") == "MSFT"

def test_provider_symbol_in_future():
    # Future India support
    assert compute_provider_symbol("RELIANCE", "IN", "NSE") == "RELIANCE.NS"
    assert compute_provider_symbol("TCS", "IN", "BSE") == "TCS.BO"

