from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.db.database import Base

class RunType(str, enum.Enum):
    RESEARCH = "RESEARCH"
    EXPLAIN = "EXPLAIN"

class TriggerType(str, enum.Enum):
    PRICE_MOVE = "PRICE_MOVE"
    FILING_EVENT = "FILING_EVENT"
    SCHEDULED = "SCHEDULED"

class RunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=True, unique=True, index=True)

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    
    user = relationship("User", backref="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")

class Holding(Base):
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker_symbol = Column(String, nullable=False)
    marketplace = Column(String, nullable=False)  # "US", "IN", etc.
    exchange = Column(String, nullable=False)  # "NASDAQ", "NYSE", "NSE", "BSE", etc.
    provider_symbol = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    buy_date = Column(Date, nullable=False)
    buy_price = Column(Float, nullable=False)
    broker = Column(String, nullable=True)
    currency = Column(String, nullable=True, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="holdings")

class ResearchRun(Base):
    __tablename__ = "research_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    run_type = Column(SQLEnum(RunType), nullable=False)
    trigger_type = Column(SQLEnum(TriggerType), nullable=True)
    status = Column(SQLEnum(RunStatus), nullable=False, default=RunStatus.QUEUED)
    params_json = Column(JSON, nullable=True)
    holdings_snapshot_json = Column(JSON, nullable=True)
    warnings_json = Column(JSON, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    report_md = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
    portfolio = relationship("Portfolio")
    sources = relationship("RunSource", back_populates="run", cascade="all, delete-orphan")

class RunSource(Base):
    __tablename__ = "run_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("research_runs.id"), nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    
    run = relationship("ResearchRun", back_populates="sources")

class CanonicalSector(Base):
    __tablename__ = "canonical_sectors"
    
    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String, unique=True, nullable=False)
    is_active = Column(Integer, default=1)

class SectorAlias(Base):
    __tablename__ = "sector_aliases"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False)  # e.g., "yfinance"
    alias = Column(String, nullable=False)  # e.g., "Technology"
    canonical_sector_id = Column(Integer, ForeignKey("canonical_sectors.id"), nullable=False)
    
    canonical_sector = relationship("CanonicalSector")

class SectorETFProxy(Base):
    __tablename__ = "sector_etf_proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String, nullable=False)  # "US", "IN", etc.
    canonical_sector_id = Column(Integer, ForeignKey("canonical_sectors.id"), nullable=False)
    etf_symbol = Column(String, nullable=False)
    is_active = Column(Integer, default=1)
    
    canonical_sector = relationship("CanonicalSector")

