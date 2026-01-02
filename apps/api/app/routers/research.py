from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import ResearchRun, Portfolio, Holding, RunType, RunStatus, User
from app.services.portfolio_metrics import compute_portfolio_metrics
import uuid
import json
import os
import httpx

router = APIRouter()

DEMO_USER_ID = 1
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/research/start")

class ResearchRunRequest(BaseModel):
    portfolio_id: int
    preferences: dict = {}
    strategy: str = "default"

@router.post("/run")
async def create_research_run(request: ResearchRunRequest, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == request.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    holdings = db.query(Holding).filter(Holding.portfolio_id == request.portfolio_id).all()
    
    # Create holdings snapshot
    holdings_snapshot = [
        {
            "id": h.id,
            "ticker_symbol": h.ticker_symbol,
            "marketplace": h.marketplace,
            "exchange": h.exchange,
            "provider_symbol": h.provider_symbol,
            "quantity": h.quantity,
            "buy_date": h.buy_date.isoformat(),
            "buy_price": h.buy_price,
            "broker": h.broker,
            "currency": h.currency
        }
        for h in holdings
    ]
    
    # Compute metrics (backend-owned calculation)
    metrics = compute_portfolio_metrics(db, holdings)
    
    # Create run
    run_id = uuid.uuid4()
    run = ResearchRun(
        id=run_id,
        user_id=DEMO_USER_ID,
        portfolio_id=request.portfolio_id,
        run_type=RunType.RESEARCH,
        status=RunStatus.QUEUED,
        params_json={
            "preferences": request.preferences,
            "strategy": request.strategy
        },
        holdings_snapshot_json=holdings_snapshot,
        metrics_json=metrics
    )
    db.add(run)
    db.commit()
    
    # Trigger n8n webhook
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                N8N_WEBHOOK_URL,
                json={
                    "run_id": str(run_id),
                    "portfolio_id": request.portfolio_id,
                    "metrics": metrics,
                    "holdings_snapshot": holdings_snapshot
                },
                timeout=5.0
            )
        # Update status to RUNNING
        run.status = RunStatus.RUNNING
        db.commit()
    except Exception as e:
        # If webhook fails, mark as failed
        run.status = RunStatus.FAILED
        run.warnings_json = {"error": str(e)}
        db.commit()
    
    return {"run_id": str(run_id), "status": run.status.value}

