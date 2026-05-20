"""Tests for app.services.edgar.cik_sync."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import SecCompany
from app.services.edgar.cik_sync import upsert_companies


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    SecCompany.__table__.create(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_upsert_companies_inserts(db):
    entries = [
        {"cik_str": 320193, "ticker": "aapl", "title": "Apple Inc."},
        {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp."},
    ]
    count = upsert_companies(db, entries)
    assert count == 2
    rows = db.query(SecCompany).order_by(SecCompany.cik).all()
    assert [r.cik for r in rows] == ["0000320193", "0000789019"]
    assert rows[0].ticker == "AAPL"
    assert rows[0].name == "Apple Inc."


def test_upsert_companies_is_idempotent(db):
    entries = [{"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}]
    upsert_companies(db, entries)
    upsert_companies(db, entries)
    upsert_companies(db, entries)
    assert db.query(SecCompany).count() == 1


def test_upsert_companies_updates_existing(db):
    upsert_companies(db, [{"cik_str": 320193, "ticker": "AAPL", "title": "Old Name"}])
    upsert_companies(db, [{"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}])
    company = db.get(SecCompany, "0000320193")
    assert company.name == "Apple Inc."
    assert db.query(SecCompany).count() == 1


def test_upsert_companies_skips_missing_fields(db):
    entries = [
        {"cik_str": 320193, "ticker": "AAPL"},  # missing title
        {"ticker": "FOO", "title": "Foo"},  # missing cik
        {"cik_str": 1, "title": "Bar"},  # missing ticker
    ]
    count = upsert_companies(db, entries)
    assert count == 0
    assert db.query(SecCompany).count() == 0
