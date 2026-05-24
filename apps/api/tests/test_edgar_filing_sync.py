"""Tests for app.services.edgar.filing_sync."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import SecCompany, SecFiling
from app.services.edgar.filing_sync import (
    insert_filings,
    iter_recent_filings,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    SecCompany.__table__.create(engine)
    SecFiling.__table__.create(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    session.add(SecCompany(cik="0000320193", ticker="AAPL", name="Apple Inc."))
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _submissions_payload():
    return {
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000010", "0000320193-26-000011"],
                "form": ["10-Q", "8-K"],
                "filingDate": ["2026-05-01", "2026-05-12"],
                "acceptanceDateTime": ["2026-05-01T16:00:00.000Z", "2026-05-12T08:30:00.000Z"],
                "reportDate": ["2026-03-31", ""],
                "primaryDocument": ["aapl-20260331.htm", "aapl-8k.htm"],
            }
        }
    }


def test_iter_recent_filings_yields_entries():
    rows = list(iter_recent_filings(_submissions_payload()))
    assert len(rows) == 2
    assert rows[0]["accessionNumber"] == "0000320193-26-000010"
    assert rows[0]["form"] == "10-Q"


def test_insert_filings_basic(db):
    rows = list(iter_recent_filings(_submissions_payload()))
    n = insert_filings(db, "320193", rows)
    assert n == 2
    filings = db.query(SecFiling).order_by(SecFiling.accession_no).all()
    assert [f.form_type for f in filings] == ["10-Q", "8-K"]
    assert filings[0].cik == "0000320193"
    assert filings[0].primary_doc_url.endswith("aapl-20260331.htm")


def test_insert_filings_idempotent_on_accession_no(db):
    rows = list(iter_recent_filings(_submissions_payload()))
    n1 = insert_filings(db, "320193", rows)
    n2 = insert_filings(db, "320193", rows)
    assert n1 == 2
    assert n2 == 0
    assert db.query(SecFiling).count() == 2


def test_insert_filings_respects_form_filter(db):
    rows = list(iter_recent_filings(_submissions_payload()))
    n = insert_filings(db, "320193", rows, form_types={"10-Q"})
    assert n == 1
    assert db.query(SecFiling).count() == 1
    assert db.query(SecFiling).one().form_type == "10-Q"


def test_insert_filings_skips_unknown_forms(db):
    payload = {
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000099"],
                "form": ["SC 13G"],
                "filingDate": ["2026-04-01"],
                "acceptanceDateTime": [""],
                "reportDate": [""],
                "primaryDocument": ["x.htm"],
            }
        }
    }
    rows = list(iter_recent_filings(payload))
    n = insert_filings(db, "320193", rows)
    assert n == 0
