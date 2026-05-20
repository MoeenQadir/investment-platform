from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import numpy as np
from app.services.sector import resolve_sector_etf, get_market_etf
from app.services.providers import get_provider
from app.utils.time import utcnow


def get_days_since_filing(db: Session, ticker: str) -> Optional[int]:
    """Return whole days since the most recent 10-K/10-Q/8-K filing for `ticker`.

    Returns None if no company or filing is found.
    """
    from app.db.models import SecCompany, SecFiling

    if not ticker:
        return None
    company = (
        db.query(SecCompany)
        .filter(SecCompany.ticker == ticker.upper())
        .first()
    )
    if company is None:
        return None
    filing = (
        db.query(SecFiling)
        .filter(SecFiling.cik == company.cik)
        .filter(SecFiling.form_type.in_(["10-K", "10-Q", "8-K"]))
        .order_by(SecFiling.filed_at.desc())
        .first()
    )
    if filing is None or filing.filed_at is None:
        return None
    delta = utcnow() - filing.filed_at
    return max(delta.days, 0)


def get_days_since_form4(db: Session, ticker: str) -> Optional[int]:
    """Return whole days since the most recent Form 4 transaction for `ticker`."""
    from app.db.models import SecCompany, SecForm4Transaction

    if not ticker:
        return None
    company = (
        db.query(SecCompany)
        .filter(SecCompany.ticker == ticker.upper())
        .first()
    )
    if company is None:
        return None
    txn = (
        db.query(SecForm4Transaction)
        .filter(SecForm4Transaction.issuer_cik == company.cik)
        .order_by(SecForm4Transaction.transaction_date.desc())
        .first()
    )
    if txn is None or txn.transaction_date is None:
        return None
    delta = datetime.now().date() - txn.transaction_date
    return max(delta.days, 0)

def score_market_driver(stock_return: float, market_etf: str = "SPY") -> float:
    """Score market-wide driver (0..1).
    
    base = min(1, abs(r_SPY)/0.015)
    align = 1.0 if sign(r_stock)==sign(r_SPY) else 0.3
    score_market = base*align
    """
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=5)

        hist = get_provider().fetch_stock_data(market_etf, start_date, end_date)
        if hist is None or len(hist) < 2:
            return 0.0

        market_return = hist['Close'].pct_change().iloc[-1]

        base = min(1.0, abs(market_return) / 0.015)
        align = 1.0 if np.sign(stock_return) == np.sign(market_return) else 0.3
        return base * align
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return 0.0

def score_sector_driver(stock_return: float, sector_etf: str) -> float:
    """Score sector-wide driver (0..1). Same formula as market."""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=5)

        hist = get_provider().fetch_stock_data(sector_etf, start_date, end_date)
        if hist is None or len(hist) < 2:
            return 0.0

        sector_return = hist['Close'].pct_change().iloc[-1]

        base = min(1.0, abs(sector_return) / 0.02)
        align = 1.0 if np.sign(stock_return) == np.sign(sector_return) else 0.3
        return base * align
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return 0.0

def score_filings_driver(days_since_filing: Optional[int]) -> float:
    """Score filings/fundamentals driver (0..1).
    
    recency = 1.0 if <=3d, 0.7 if <=7d, 0.4 if <=14d else 0
    delta_flag: v1 placeholder -> 0.5 when filing exists
    """
    if days_since_filing is None:
        return 0.0
    
    if days_since_filing <= 3:
        recency = 1.0
    elif days_since_filing <= 7:
        recency = 0.7
    elif days_since_filing <= 14:
        recency = 0.4
    else:
        return 0.0
    
    # v1: delta_flag placeholder (would check price_move trigger + filing event)
    delta_flag = 0.5  # Placeholder
    return recency * delta_flag

def score_insider_driver(days_since_form4: Optional[int]) -> float:
    """Score insider activity driver (0..1).
    
    recency as above
    intensity_factor: 1.0 if exists else 0
    """
    if days_since_form4 is None:
        return 0.0
    
    if days_since_form4 <= 3:
        recency = 1.0
    elif days_since_form4 <= 7:
        recency = 0.7
    elif days_since_form4 <= 14:
        recency = 0.4
    else:
        return 0.0
    
    intensity_factor = 1.0  # v1: exists = 1.0
    return recency * intensity_factor

def score_flow_technical_driver(stock_return: float, volatility: float) -> float:
    """Score flow/technical driver (0..1).
    
    v1: min(1, abs(r_stock)/(2*σ_stock))
    """
    if volatility == 0:
        return 0.0
    return min(1.0, abs(stock_return) / (2 * volatility))

def determine_driver_count(scores: Dict[str, float]) -> int:
    """Determine dynamic driver count (3 or 5).
    
    strong = count(scores >= 0.6)
    medium = count(0.4 <= score < 0.6)
    if strong >= 4 OR (strong >= 3 AND medium >= 2) -> 5; else 3
    """
    strong = sum(1 for s in scores.values() if s >= 0.6)
    medium = sum(1 for s in scores.values() if 0.4 <= s < 0.6)
    
    if strong >= 4 or (strong >= 3 and medium >= 2):
        return 5
    return 3

def score_drivers_for_event(
    db: Session,
    provider_symbol: str,
    stock_return: float,
    volatility: float,
    marketplace: str,
    canonical_sector_id: Optional[int] = None,
    days_since_filing: Optional[int] = None,
    days_since_form4: Optional[int] = None,
    ticker: Optional[str] = None,
) -> Dict:
    """Score all drivers and return ranked list.
    
    Returns dict with 'drivers' (list of driver dicts with name, score, metrics, references),
    'driver_count', 'scores' (raw scores dict).
    """
    from app.db.models import CanonicalSector
    
    scores = {}
    
    # Market driver
    market_etf = get_market_etf(marketplace)
    scores['market'] = score_market_driver(stock_return, market_etf)
    
    # Sector driver
    if canonical_sector_id:
        canonical_sector = db.query(CanonicalSector).filter(
            CanonicalSector.id == canonical_sector_id
        ).first()
        if canonical_sector:
            sector_etf = resolve_sector_etf(db, marketplace, canonical_sector)
            if sector_etf:
                scores['sector'] = score_sector_driver(stock_return, sector_etf)
            else:
                scores['sector'] = 0.0
        else:
            scores['sector'] = 0.0
    else:
        scores['sector'] = 0.0
    
    lookup_ticker = ticker or provider_symbol

    if days_since_filing is None and lookup_ticker:
        days_since_filing = get_days_since_filing(db, lookup_ticker)
    scores['filings'] = score_filings_driver(days_since_filing)

    if days_since_form4 is None and lookup_ticker:
        days_since_form4 = get_days_since_form4(db, lookup_ticker)
    scores['insider'] = score_insider_driver(days_since_form4)
    
    # Flow/technical driver
    scores['flow_technical'] = score_flow_technical_driver(stock_return, volatility)
    
    # Determine driver count
    driver_count = determine_driver_count(scores)
    
    # Build driver list (sorted by score, top N)
    driver_names = {
        'market': 'Market-wide movement',
        'sector': 'Sector-wide movement',
        'filings': 'Recent filings/fundamentals',
        'insider': 'Insider activity',
        'flow_technical': 'Flow/technical factors'
    }
    
    sorted_drivers = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_drivers = sorted_drivers[:driver_count]
    
    drivers = []
    for name, score in top_drivers:
        if score > 0:  # Guardrail: only output with evidence
            drivers.append({
                'name': driver_names[name],
                'score': score,
                'metrics': {
                    'score_value': score,
                    'category': name
                },
                'references': []  # Would include URLs in real implementation
            })
    
    return {
        'drivers': drivers,
        'driver_count': len(drivers),
        'scores': scores
    }
