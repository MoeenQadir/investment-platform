import sys
import os
# Add parent directory to path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.db.models import Base, CanonicalSector, SectorAlias, SectorETFProxy, User, Portfolio, Holding
from app.services.finance import compute_provider_symbol
from datetime import date

# Create tables
Base.metadata.create_all(bind=engine)

db: Session = SessionLocal()

try:
    # Create demo user
    demo_user = db.query(User).filter(User.id == 1).first()
    if not demo_user:
        demo_user = User(id=1, email="demo@example.com")
        db.add(demo_user)
        db.commit()
    
    # Seed canonical sectors (US SPDR sectors)
    sectors_data = [
        "Technology",
        "Financial Services",
        "Healthcare",
        "Energy",
        "Consumer Cyclical",
        "Consumer Defensive",
        "Industrials",
        "Basic Materials",
        "Utilities",
        "Real Estate",
        "Communication Services"
    ]
    
    sector_map = {}
    for sector_name in sectors_data:
        existing = db.query(CanonicalSector).filter(CanonicalSector.canonical_name == sector_name).first()
        if not existing:
            sector = CanonicalSector(canonical_name=sector_name, is_active=1)
            db.add(sector)
            db.flush()
            sector_map[sector_name] = sector.id
        else:
            sector_map[sector_name] = existing.id
    
    # Sector ETF mapping (SPDR ETFs)
    etf_mapping = {
        "Technology": "XLK",
        "Financial Services": "XLF",
        "Healthcare": "XLV",
        "Energy": "XLE",
        "Consumer Cyclical": "XLY",
        "Consumer Defensive": "XLP",
        "Industrials": "XLI",
        "Basic Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication Services": "XLC"
    }
    
    for sector_name, etf_symbol in etf_mapping.items():
        sector_id = sector_map.get(sector_name)
        if sector_id:
            existing = db.query(SectorETFProxy).filter(
                SectorETFProxy.marketplace == "US",
                SectorETFProxy.canonical_sector_id == sector_id,
                SectorETFProxy.etf_symbol == etf_symbol
            ).first()
            if not existing:
                proxy = SectorETFProxy(
                    marketplace="US",
                    canonical_sector_id=sector_id,
                    etf_symbol=etf_symbol,
                    is_active=1
                )
                db.add(proxy)
    
    # Add sector aliases (yfinance sector strings -> canonical)
    alias_mapping = {
        "Technology": ["Technology", "Information Technology"],
        "Financial Services": ["Financial Services", "Financial"],
        "Healthcare": ["Healthcare"],
        "Energy": ["Energy"],
        "Consumer Cyclical": ["Consumer Cyclical", "Consumer Discretionary"],
        "Consumer Defensive": ["Consumer Defensive", "Consumer Staples"],
        "Industrials": ["Industrials", "Industrial"],
        "Basic Materials": ["Basic Materials", "Materials"],
        "Utilities": ["Utilities"],
        "Real Estate": ["Real Estate", "Real Estate Investment Trusts"],
        "Communication Services": ["Communication Services", "Telecommunication Services"]
    }
    
    for canonical_name, aliases in alias_mapping.items():
        sector_id = sector_map.get(canonical_name)
        if sector_id:
            for alias in aliases:
                existing = db.query(SectorAlias).filter(
                    SectorAlias.provider == "yfinance",
                    SectorAlias.alias == alias
                ).first()
                if not existing:
                    sector_alias = SectorAlias(
                        provider="yfinance",
                        alias=alias,
                        canonical_sector_id=sector_id
                    )
                    db.add(sector_alias)
    
    db.commit()
    
    # Create demo portfolio with sample holdings
    demo_portfolio = db.query(Portfolio).filter(Portfolio.name == "Demo Portfolio").first()
    if not demo_portfolio:
        demo_portfolio = Portfolio(user_id=1, name="Demo Portfolio")
        db.add(demo_portfolio)
        db.flush()
        
        # Add sample holdings
        sample_holdings = [
            {
                "ticker_symbol": "AAPL",
                "marketplace": "US",
                "exchange": "NASDAQ",
                "quantity": 10.0,
                "buy_date": date(2024, 1, 1),
                "buy_price": 180.00,
                "broker": "Demo Broker",
                "currency": "USD"
            },
            {
                "ticker_symbol": "MSFT",
                "marketplace": "US",
                "exchange": "NASDAQ",
                "quantity": 5.0,
                "buy_date": date(2024, 1, 15),
                "buy_price": 350.00,
                "broker": "Demo Broker",
                "currency": "USD"
            }
        ]
        
        for holding_data in sample_holdings:
            provider_symbol = compute_provider_symbol(
                holding_data["ticker_symbol"],
                holding_data["marketplace"],
                holding_data["exchange"]
            )
            holding = Holding(
                portfolio_id=demo_portfolio.id,
                provider_symbol=provider_symbol,
                **{k: v for k, v in holding_data.items() if k != "ticker_symbol"}
            )
            holding.ticker_symbol = holding_data["ticker_symbol"]
            db.add(holding)
        
        db.commit()
        print("Demo portfolio created with sample holdings")
    
    print("Seed data completed successfully!")
    
except Exception as e:
    db.rollback()
    print(f"Error seeding data: {e}")
    raise
finally:
    db.close()

