"""Shared pytest fixtures for the api test suite."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def in_memory_db():
    """Yield a SQLAlchemy Session bound to an in-memory SQLite database.

    All models from app.db.models are created in the fresh schema. Each test
    that requests this fixture gets an isolated database.
    """
    from app.db.models import SecCompany, SecFiling, SecForm4Transaction

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    SecCompany.__table__.create(engine)
    SecFiling.__table__.create(engine)
    SecForm4Transaction.__table__.create(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        SecForm4Transaction.__table__.drop(engine)
        SecFiling.__table__.drop(engine)
        SecCompany.__table__.drop(engine)
        engine.dispose()
