"""Tests for the EDGAR-backed helpers in app.services.drivers."""
from __future__ import annotations

from datetime import date, timedelta

from app.db.models import SecCompany, SecFiling, SecForm4Transaction
from app.services.drivers import get_days_since_filing, get_days_since_form4
from app.utils.time import utcnow


def _add_company(db, cik: str = "0000320193", ticker: str = "AAPL") -> SecCompany:
    company = SecCompany(cik=cik, ticker=ticker, name="Apple Inc.")
    db.add(company)
    db.commit()
    return company


def test_get_days_since_filing_returns_delta(in_memory_db):
    _add_company(in_memory_db)
    filed_at = utcnow() - timedelta(days=4, hours=2)
    in_memory_db.add(
        SecFiling(
            cik="0000320193",
            accession_no="0000320193-26-000001",
            form_type="10-Q",
            filed_at=filed_at,
        )
    )
    in_memory_db.commit()

    days = get_days_since_filing(in_memory_db, "AAPL")
    assert days == 4


def test_get_days_since_filing_picks_most_recent(in_memory_db):
    _add_company(in_memory_db)
    now = utcnow()
    in_memory_db.add_all([
        SecFiling(
            cik="0000320193", accession_no="A1", form_type="10-K",
            filed_at=now - timedelta(days=30),
        ),
        SecFiling(
            cik="0000320193", accession_no="A2", form_type="8-K",
            filed_at=now - timedelta(days=2),
        ),
        SecFiling(
            cik="0000320193", accession_no="A3", form_type="10-Q",
            filed_at=now - timedelta(days=10),
        ),
    ])
    in_memory_db.commit()

    assert get_days_since_filing(in_memory_db, "AAPL") == 2


def test_get_days_since_filing_ignores_non_periodic_forms(in_memory_db):
    _add_company(in_memory_db)
    now = utcnow()
    in_memory_db.add_all([
        SecFiling(
            cik="0000320193", accession_no="F1", form_type="4",
            filed_at=now - timedelta(days=1),
        ),
        SecFiling(
            cik="0000320193", accession_no="F2", form_type="10-K",
            filed_at=now - timedelta(days=20),
        ),
    ])
    in_memory_db.commit()

    # Form 4 must be ignored; only 10-K counts
    assert get_days_since_filing(in_memory_db, "AAPL") == 20


def test_get_days_since_filing_no_company(in_memory_db):
    assert get_days_since_filing(in_memory_db, "NOPE") is None


def test_get_days_since_filing_no_matching_filing(in_memory_db):
    _add_company(in_memory_db)
    assert get_days_since_filing(in_memory_db, "AAPL") is None


def test_get_days_since_filing_case_insensitive_ticker(in_memory_db):
    _add_company(in_memory_db)
    in_memory_db.add(
        SecFiling(
            cik="0000320193", accession_no="X1", form_type="10-K",
            filed_at=utcnow() - timedelta(days=5),
        )
    )
    in_memory_db.commit()
    assert get_days_since_filing(in_memory_db, "aapl") == 5


def test_get_days_since_filing_empty_ticker(in_memory_db):
    assert get_days_since_filing(in_memory_db, "") is None


def test_get_days_since_form4_returns_delta(in_memory_db):
    _add_company(in_memory_db)
    in_memory_db.add(
        SecFiling(
            cik="0000320193", accession_no="F1", form_type="4",
            filed_at=utcnow() - timedelta(days=3),
        )
    )
    in_memory_db.flush()
    filing = in_memory_db.query(SecFiling).first()
    txn_date = date.today() - timedelta(days=7)
    in_memory_db.add(
        SecForm4Transaction(
            filing_id=filing.id,
            cik="0000320193",
            issuer_cik="0000320193",
            issuer_ticker="AAPL",
            insider_name="Insider A",
            transaction_date=txn_date,
            transaction_code="P",
            shares=100.0,
            price_per_share=50.0,
        )
    )
    in_memory_db.commit()

    assert get_days_since_form4(in_memory_db, "AAPL") == 7


def test_get_days_since_form4_picks_most_recent(in_memory_db):
    _add_company(in_memory_db)
    in_memory_db.add(
        SecFiling(
            cik="0000320193", accession_no="F1", form_type="4",
            filed_at=utcnow(),
        )
    )
    in_memory_db.flush()
    filing = in_memory_db.query(SecFiling).first()

    today = date.today()
    for delta_days, code in [(30, "P"), (1, "S"), (15, "P")]:
        in_memory_db.add(
            SecForm4Transaction(
                filing_id=filing.id,
                cik="0000320193",
                issuer_cik="0000320193",
                issuer_ticker="AAPL",
                insider_name="Insider",
                transaction_date=today - timedelta(days=delta_days),
                transaction_code=code,
                shares=10.0,
            )
        )
    in_memory_db.commit()

    assert get_days_since_form4(in_memory_db, "AAPL") == 1


def test_get_days_since_form4_no_company(in_memory_db):
    assert get_days_since_form4(in_memory_db, "NOPE") is None


def test_get_days_since_form4_no_transactions(in_memory_db):
    _add_company(in_memory_db)
    assert get_days_since_form4(in_memory_db, "AAPL") is None


def test_get_days_since_form4_empty_ticker(in_memory_db):
    assert get_days_since_form4(in_memory_db, "") is None
