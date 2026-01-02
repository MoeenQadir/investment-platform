from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import portfolio, research, explain, runs, webhooks
from app.db.database import engine
from app.db import models
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Investment Research API",
    description="API for investment research and explanation workflows",
    version="1.0.0"
)

# CORS configuration - allow multiple origins from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(explain.router, prefix="/api/explain", tags=["explain"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(webhooks.router, prefix="/api/webhooks/n8n", tags=["webhooks"])

@app.get("/")
async def root():
    return {"message": "Investment Research API"}

