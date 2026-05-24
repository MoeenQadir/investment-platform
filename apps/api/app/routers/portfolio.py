from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.auth import get_current_user
from app.db.database import get_db
from app.db.models import Portfolio, Holding, User
from app.services.finance import compute_provider_symbol

router = APIRouter()

class PortfolioCreate(BaseModel):
    name: str

class PortfolioResponse(BaseModel):
    id: int
    name: str
    user_id: int
    
    class Config:
        from_attributes = True

class HoldingCreate(BaseModel):
    ticker_symbol: str
    marketplace: str
    exchange: str
    quantity: float
    buy_date: date  # ISO date is parsed into date
    buy_price: float
    broker: str = None
    currency: str = "USD"

class HoldingResponse(BaseModel):
    id: int
    ticker_symbol: str
    marketplace: str
    exchange: str
    provider_symbol: str
    quantity: float
    buy_date: date
    buy_price: float
    broker: str = None
    currency: str = None
    
    class Config:
        from_attributes = True

def _get_owned_portfolio(db: Session, portfolio_id: int, user_id: int) -> Portfolio:
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get("", response_model=List[PortfolioResponse])
def list_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Portfolio).filter(Portfolio.user_id == current_user.id).all()


@router.post("", response_model=PortfolioResponse)
def create_portfolio(
    portfolio: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_portfolio = Portfolio(name=portfolio.name, user_id=current_user.id)
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

@router.get("/{portfolio_id}", response_model=PortfolioResponse)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_portfolio(db, portfolio_id, current_user.id)

@router.post("/{portfolio_id}/holdings", response_model=List[HoldingResponse])
def bulk_upsert_holdings(
    portfolio_id: int,
    holdings: List[HoldingCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_portfolio(db, portfolio_id, current_user.id)
    
    result = []
    for holding_data in holdings:
        provider_symbol = compute_provider_symbol(
            holding_data.ticker_symbol,
            holding_data.marketplace,
            holding_data.exchange
        )
        
        # For v1: simple upsert (delete existing and create new)
        # In production, use proper upsert logic
        existing = db.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.ticker_symbol == holding_data.ticker_symbol
        ).first()
        
        if existing:
            db.delete(existing)
        
        buy_date = holding_data.buy_date
        
        holding = Holding(
            portfolio_id=portfolio_id,
            ticker_symbol=holding_data.ticker_symbol,
            marketplace=holding_data.marketplace,
            exchange=holding_data.exchange,
            provider_symbol=provider_symbol,
            quantity=holding_data.quantity,
            buy_date=buy_date,
            buy_price=holding_data.buy_price,
            broker=holding_data.broker,
            currency=holding_data.currency or "USD"
        )
        db.add(holding)
        result.append(holding)
    
    db.commit()
    for holding in result:
        db.refresh(holding)
    
    return result

@router.get("/{portfolio_id}/holdings", response_model=List[HoldingResponse])
def get_holdings(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_portfolio(db, portfolio_id, current_user.id)
    holdings = db.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()
    return holdings

