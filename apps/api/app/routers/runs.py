from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.db.models import ResearchRun, RunType, RunStatus
import uuid

router = APIRouter()

@router.get("")
def list_runs(
    run_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    portfolio_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ResearchRun)
    
    if run_type:
        query = query.filter(ResearchRun.run_type == RunType(run_type))
    if status:
        query = query.filter(ResearchRun.status == RunStatus(status))
    if portfolio_id:
        query = query.filter(ResearchRun.portfolio_id == portfolio_id)
    
    runs = query.order_by(ResearchRun.created_at.desc()).limit(100).all()
    
    return [
        {
            "id": str(run.id),
            "run_type": run.run_type.value,
            "trigger_type": run.trigger_type.value if run.trigger_type else None,
            "status": run.status.value,
            "portfolio_id": run.portfolio_id,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat()
        }
        for run in runs
    ]

@router.get("/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        return {"error": "Invalid run_id"}
    
    run = db.query(ResearchRun).filter(ResearchRun.id == run_uuid).first()
    if not run:
        return {"error": "Run not found"}
    
    return {
        "id": str(run.id),
        "run_type": run.run_type.value,
        "trigger_type": run.trigger_type.value if run.trigger_type else None,
        "status": run.status.value,
        "portfolio_id": run.portfolio_id,
        "params_json": run.params_json,
        "holdings_snapshot_json": run.holdings_snapshot_json,
        "warnings_json": run.warnings_json,
        "metrics_json": run.metrics_json,
        "report_md": run.report_md,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
        "sources": [
            {
                "id": s.id,
                "title": s.title,
                "url": s.url,
                "retrieved_at": s.retrieved_at.isoformat()
            }
            for s in run.sources
        ]
    }

