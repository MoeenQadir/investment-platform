import hmac
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import ResearchRun, RunStatus, RunSource

router = APIRouter()


def verify_n8n_secret(
    x_n8n_secret: Optional[str] = Header(default=None, alias="X-N8N-Secret"),
) -> None:
    """Constant-time check of the shared secret n8n sends on every webhook call.

    Set N8N_WEBHOOK_SECRET in both the API env and n8n's HTTP Request node
    Authorization config. Missing env var on the API side means the gate is
    effectively open — fail closed if the var is set but the header doesn't match.
    """
    expected = os.getenv("N8N_WEBHOOK_SECRET", "").strip()
    if not expected:
        # No secret configured — preserve dev-loop behaviour. Production deploys MUST set this.
        return
    if not x_n8n_secret or not hmac.compare_digest(x_n8n_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-N8N-Secret header",
        )

class Source(BaseModel):
    title: str
    url: str

class CompleteRequest(BaseModel):
    run_id: str
    status: str  # "COMPLETED" or "COMPLETED_WITH_WARNINGS"
    warnings: Optional[dict] = None
    metrics_json: Optional[dict] = None
    report_md: Optional[str] = None
    sources: Optional[List[Source]] = []

class FailRequest(BaseModel):
    run_id: str
    error_type: str
    message: str
    partial_metrics_json: Optional[dict] = None

@router.post("/complete", dependencies=[Depends(verify_n8n_secret)])
def webhook_complete(request: CompleteRequest, db: Session = Depends(get_db)):
    try:
        run_uuid = uuid.UUID(request.run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id")
    
    run = db.query(ResearchRun).filter(ResearchRun.id == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    status_map = {
        "COMPLETED": RunStatus.COMPLETED,
        "COMPLETED_WITH_WARNINGS": RunStatus.COMPLETED_WITH_WARNINGS
    }
    
    run.status = status_map.get(request.status, RunStatus.COMPLETED)
    if request.warnings:
        run.warnings_json = request.warnings
    if request.metrics_json:
        run.metrics_json = request.metrics_json
    if request.report_md:
        run.report_md = request.report_md
    
    db.commit()
    
    # Add sources
    if request.sources:
        for source_data in request.sources:
            source = RunSource(
                run_id=run_uuid,
                title=source_data.title,
                url=source_data.url
            )
            db.add(source)
        db.commit()
    
    return {"status": "ok", "run_id": request.run_id}

@router.post("/fail", dependencies=[Depends(verify_n8n_secret)])
def webhook_fail(request: FailRequest, db: Session = Depends(get_db)):
    try:
        run_uuid = uuid.UUID(request.run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id")
    
    run = db.query(ResearchRun).filter(ResearchRun.id == run_uuid).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run.status = RunStatus.FAILED
    run.warnings_json = {
        "error_type": request.error_type,
        "message": request.message,
        "partial_metrics": request.partial_metrics_json
    }
    db.commit()
    
    return {"status": "ok", "run_id": request.run_id}

