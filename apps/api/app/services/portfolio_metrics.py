from typing import Dict, List
from datetime import date
from sqlalchemy.orm import Session
from app.db.models import Holding
from app.services.finance import compute_returns, compute_volatility
from app.services.providers import get_provider
from app.services.sector import resolve_canonical_sector


def compute_portfolio_metrics(
    db: Session,
    holdings: List[Holding],
    benchmark_etf: str = "SPY",
) -> Dict:
    """Compute portfolio-level metrics: exposure, performance, benchmarks."""
    if not holdings:
        return {
            'sector_exposure': {},
            'market_cap_exposure': {},
            'holdings_performance': [],
            'portfolio_total_return': 0.0,
            'benchmark_comparison': {},
        }

    provider = get_provider()

    total_value = 0.0
    holding_values: Dict[int, float] = {}

    for holding in holdings:
        price = provider.get_latest_price(holding.provider_symbol)
        if price is None:
            price = float(holding.buy_price)
        value = price * float(holding.quantity)
        holding_values[holding.id] = value
        total_value += value

    sector_weights: Dict[str, float] = {}
    holdings_performance: List[Dict] = []

    for holding in holdings:
        weight = holding_values.get(holding.id, 0) / total_value if total_value > 0 else 0

        # Sector resolution via provider, then canonical mapping.
        sector_name = "Unknown"
        provider_sector = provider.get_sector(holding.provider_symbol)
        if provider_sector:
            canonical = resolve_canonical_sector(db, provider.name, provider_sector)
            sector_name = canonical.canonical_name if canonical else provider_sector

        sector_weights[sector_name] = sector_weights.get(sector_name, 0) + weight

        hist = provider.fetch_stock_data(
            holding.provider_symbol,
            holding.buy_date,
            date.today(),
        )
        if hist is not None and not hist.empty:
            buy_price = float(holding.buy_price)
            current_price = float(hist['Close'].iloc[-1])
            return_pct = ((current_price - buy_price) / buy_price) * 100

            returns = compute_returns(hist['Close'])
            vol = compute_volatility(returns) if len(returns) > 0 else 0.0

            holdings_performance.append({
                'holding_id': holding.id,
                'ticker_symbol': holding.ticker_symbol,
                'return_pct': float(return_pct),
                'volatility': float(vol),
                'current_price': float(current_price),
                'buy_price': float(buy_price),
                'value': float(holding_values.get(holding.id, 0)),
            })
        else:
            holdings_performance.append({
                'holding_id': holding.id,
                'ticker_symbol': holding.ticker_symbol,
                'return_pct': 0.0,
                'volatility': 0.0,
                'current_price': float(holding.buy_price),
                'buy_price': float(holding.buy_price),
                'value': float(holding_values.get(holding.id, 0)),
            })

    portfolio_return = sum(
        hp['return_pct'] * (holding_values.get(hp['holding_id'], 0) / total_value)
        for hp in holdings_performance
        if total_value > 0
    )

    benchmark_return = 0.0
    excess_return = 0.0
    try:
        avg_buy_date = min(h.buy_date for h in holdings)
        bench_hist = provider.fetch_stock_data(benchmark_etf, avg_buy_date, date.today())
        if bench_hist is not None and not bench_hist.empty:
            bench_start = float(bench_hist['Close'].iloc[0])
            bench_end = float(bench_hist['Close'].iloc[-1])
            benchmark_return = ((bench_end - bench_start) / bench_start) * 100
            excess_return = portfolio_return - benchmark_return
    except Exception:
        pass

    return {
        'sector_exposure': sector_weights,
        'market_cap_exposure': {},
        'holdings_performance': holdings_performance,
        'portfolio_total_return': float(portfolio_return),
        'benchmark_comparison': {
            'benchmark_return': float(benchmark_return),
            'excess_return': float(excess_return),
            'benchmark_etf': benchmark_etf,
        },
    }


def detect_price_move_events_for_portfolio(
    db: Session,
    holdings: List[Holding],
    threshold_sigma: float = 2.0,
) -> List[Dict]:
    """Detect price move events for all holdings in portfolio."""
    from app.services.finance import detect_price_move

    events = []
    for holding in holdings:
        move_info = detect_price_move(holding.provider_symbol, threshold_sigma)
        if move_info and move_info.get('triggered'):
            events.append({
                'holding_id': holding.id,
                'provider_symbol': holding.provider_symbol,
                'ticker_symbol': holding.ticker_symbol,
                **move_info,
            })
    return events
