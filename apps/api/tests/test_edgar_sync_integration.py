"""End-to-end integration tests for sync_cik_tickers + sync_filings_for_cik
using httpx.MockTransport. Verifies the HTTP layer wires correctly into the
upsert/insert helpers without touching real SEC endpoints.
"""
from __future__ import annotations

import json

import httpx
import pytest

from app.db.models import SecCompany, SecFiling
from app.services.edgar import (
    SecClient,
    sync_cik_tickers,
    sync_filings_for_cik,
)


COMPANY_TICKERS_PAYLOAD = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
    "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
}


SUBMISSIONS_PAYLOAD = {
    "cik": "320193",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000320193-26-000010",
                "0000320193-26-000009",
                "0000320193-26-000008",
            ],
            "filingDate": ["2026-05-01", "2026-04-28", "2026-04-15"],
            "reportDate": ["2026-03-31", "", "2026-03-31"],
            "acceptanceDateTime": [
                "2026-05-01T16:30:21.000Z",
                "2026-04-28T16:15:00.000Z",
                "2026-04-15T16:00:00.000Z",
            ],
            "form": ["10-Q", "8-K", "10-Q"],
            "primaryDocument": [
                "aapl-20260331.htm",
                "aapl-8k.htm",
                "aapl-20260331-q.htm",
            ],
        },
        "files": [],
    },
}


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        host = request.url.host
        if host == "www.sec.gov" and path == "/files/company_tickers.json":
            return httpx.Response(200, json=COMPANY_TICKERS_PAYLOAD)
        if host == "data.sec.gov" and path.startswith("/submissions/CIK"):
            return httpx.Response(200, json=SUBMISSIONS_PAYLOAD)
        return httpx.Response(404, text=f"unmocked: {host}{path}")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_sync_cik_tickers_end_to_end(in_memory_db, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test contact@example.com")
    client = SecClient(transport=_mock_transport(), rate_limit=10)
    try:
        rows = await sync_cik_tickers(in_memory_db, client=client)
    finally:
        await client.aclose()

    assert rows == 3
    apple = in_memory_db.get(SecCompany, "0000320193")
    assert apple is not None
    assert apple.ticker == "AAPL"
    assert apple.name == "Apple Inc."
    assert in_memory_db.get(SecCompany, "0000789019") is not None
    assert in_memory_db.get(SecCompany, "0001652044") is not None


@pytest.mark.asyncio
async def test_sync_cik_tickers_idempotent_over_http(in_memory_db, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test contact@example.com")
    client = SecClient(transport=_mock_transport(), rate_limit=10)
    try:
        first = await sync_cik_tickers(in_memory_db, client=client)
        second = await sync_cik_tickers(in_memory_db, client=client)
    finally:
        await client.aclose()

    assert first == 3 and second == 3
    assert in_memory_db.query(SecCompany).count() == 3


@pytest.mark.asyncio
async def test_sync_filings_for_cik_end_to_end(in_memory_db, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test contact@example.com")
    # SecCompany row is required for the FK on SecFiling.
    in_memory_db.add(
        SecCompany(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    in_memory_db.commit()

    client = SecClient(transport=_mock_transport(), rate_limit=10)
    try:
        inserted = await sync_filings_for_cik(
            in_memory_db, "0000320193", client=client
        )
    finally:
        await client.aclose()

    assert inserted == 3
    filings = (
        in_memory_db.query(SecFiling)
        .filter(SecFiling.cik == "0000320193")
        .all()
    )
    assert {f.form_type for f in filings} == {"10-Q", "8-K"}
    assert {f.accession_no for f in filings} == {
        "0000320193-26-000010",
        "0000320193-26-000009",
        "0000320193-26-000008",
    }


@pytest.mark.asyncio
async def test_sync_filings_idempotent_over_http(in_memory_db, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test contact@example.com")
    in_memory_db.add(
        SecCompany(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    in_memory_db.commit()

    client = SecClient(transport=_mock_transport(), rate_limit=10)
    try:
        first = await sync_filings_for_cik(in_memory_db, "0000320193", client=client)
        second = await sync_filings_for_cik(in_memory_db, "0000320193", client=client)
    finally:
        await client.aclose()

    assert first == 3
    assert second == 0
    assert in_memory_db.query(SecFiling).count() == 3


@pytest.mark.asyncio
async def test_sync_filings_form_type_filter(in_memory_db, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test contact@example.com")
    in_memory_db.add(
        SecCompany(cik="0000320193", ticker="AAPL", name="Apple Inc.")
    )
    in_memory_db.commit()

    client = SecClient(transport=_mock_transport(), rate_limit=10)
    try:
        inserted = await sync_filings_for_cik(
            in_memory_db,
            "0000320193",
            client=client,
            form_types={"10-Q"},
        )
    finally:
        await client.aclose()

    assert inserted == 2  # two 10-Qs in the payload
    forms = {
        f.form_type
        for f in in_memory_db.query(SecFiling).filter(SecFiling.cik == "0000320193")
    }
    assert forms == {"10-Q"}
