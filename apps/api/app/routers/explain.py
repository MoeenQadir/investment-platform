from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ResearchRun, Portfolio, Holding, RunType, RunStatus, TriggerType
from app.services.portfolio_metrics import detect_price_move_events_for_portfolio
from app.services.drivers import score_drivers_for_event
import uuid
import json
import os
import httpx
from pydantic import BaseModel

router = APIRouter()

DEMO_USER_ID = 1
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/explain/start")

class ExplainRunRequest(BaseModel):
    portfolio_id: int
    trigger_type: str  # "PRICE_MOVE", "FILING_EVENT", "SCHEDULED"
    trigger_payload: dict = {}

@router.post("/run")
async def create_explain_run(request: ExplainRunRequest, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == request.portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    holdings = db.query(Holding).filter(Holding.portfolio_id == request.portfolio_id).all()
    
    holdings_snapshot = [
        {
            "id": h.id,
            "ticker_symbol": h.ticker_symbol,
            "marketplace": h.marketplace,
            "exchange": h.exchange,
            "provider_symbol": h.provider_symbol,
            "quantity": h.quantity,
            "buy_date": h.buy_date.isoformat(),
            "buy_price": h.buy_price
        }
        for h in holdings
    ]
    
    # For PRICE_MOVE: detect events and score drivers
    trigger_type_enum = TriggerType(request.trigger_type)
    metrics = {}
    
    if trigger_type_enum == TriggerType.PRICE_MOVE:
        # Detect price moves
        events = detect_price_move_events_for_portfolio(db, holdings)
        if events:
            # For v1: use first event
            event = events[0]
            # Score drivers (simplified - would need sector resolution)
            # For now, compute basic metrics
            metrics = {
                "events": events,
                "selected_event": event
            }
    
    run_id = uuid.uuid4()
    run = ResearchRun(
        id=run_id,
        user_id=DEMO_USER_ID,
        portfolio_id=request.portfolio_id,
        run_type=RunType.EXPLAIN,
        trigger_type=trigger_type_enum,
        status=RunStatus.QUEUED,
        params_json=request.trigger_payload,
        holdings_snapshot_json=holdings_snapshot,
        metrics_json=metrics
    )
    db.add(run)
    db.commit()
    
    # Trigger n8n
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                N8N_WEBHOOK_URL,
                json={
                    "run_id": str(run_id),
                    "portfolio_id": request.portfolio_id,
                    "trigger_type": request.trigger_type,
                    "metrics": metrics,
                    "holdings_snapshot": holdings_snapshot
                },
                timeout=5.0
            )
        run.status = RunStatus.RUNNING
        db.commit()
    except Exception as e:
        run.status = RunStatus.FAILED
        run.warnings_json = {"error": str(e)}
        db.commit()
    
    return {"run_id": str(run_id), "status": run.status.value}

