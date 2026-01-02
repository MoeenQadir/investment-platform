from sqlalchemy.orm import Session
from typing import Optional
from app.db.models import CanonicalSector, SectorAlias, SectorETFProxy

def resolve_canonical_sector(db: Session, provider: str, provider_sector_string: str) -> Optional[CanonicalSector]:
    """Resolve a provider sector string to a canonical sector via aliases."""
    alias = db.query(SectorAlias).filter(
        SectorAlias.provider == provider,
        SectorAlias.alias == provider_sector_string
    ).first()
    
    if alias:
        return alias.canonical_sector
    
    # Try direct match on canonical name
    canonical = db.query(CanonicalSector).filter(
        CanonicalSector.canonical_name == provider_sector_string,
        CanonicalSector.is_active == 1
    ).first()
    
    return canonical

def resolve_sector_etf(db: Session, marketplace: str, canonical_sector: CanonicalSector) -> Optional[str]:
    """Resolve marketplace + canonical sector to ETF symbol."""
    proxy = db.query(SectorETFProxy).filter(
        SectorETFProxy.marketplace == marketplace,
        SectorETFProxy.canonical_sector_id == canonical_sector.id,
        SectorETFProxy.is_active == 1
    ).first()
    
    return proxy.etf_symbol if proxy else None

def get_market_etf(marketplace: str) -> str:
    """Get market-wide ETF symbol for marketplace."""
    # v1: US only -> SPY
    if marketplace == "US":
        return "SPY"
    # Future: IN -> NIFTY ETF, etc.
    return "SPY"  # Default

