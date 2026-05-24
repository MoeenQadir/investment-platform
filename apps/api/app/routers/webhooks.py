from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ResearchRun, RunStatus, RunSource
from pydantic import BaseModel
from typing import List, Optional
import uuid

router = APIRouter()

class Source(BaseModel):
    title: str
    url: str

class CompleteRequest(BaseModel):
    run_id: str
    status: str  # "COMPLETED" or "COMPLETED_WITH_WARNINGS"
    warnings: Optional[dict] = None
    metrics_json: Optional[dict] = None
    metrics: Optional[dict] = None  # alias accepted from n8n
    report_md: Optional[str] = None
    sources: Optional[List[Source]] = []

    def effective_metrics(self) -> Optional[dict]:
        return self.metrics_json or self.metrics

class FailRequest(BaseModel):
    run_id: str
    error_type: str
    message: str
    partial_metrics_json: Optional[dict] = None

@router.post("/complete")
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
    if request.effective_metrics():
        run.metrics_json = request.effective_metrics()
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

@router.post("/research-complete")
def webhook_research_complete(request: CompleteRequest, db: Session = Depends(get_db)):
    return webhook_complete(request, db)

@router.post("/fail")
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

