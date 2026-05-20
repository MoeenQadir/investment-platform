"""Sync the SEC ticker -> CIK mapping into sec_companies."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import SecCompany
from app.services.edgar.sec_client import SecClient

COMPANY_TICKERS_PATH = "/files/company_tickers.json"


def _pad_cik(cik_str: str) -> str:
    return str(cik_str).strip().zfill(10)


def _iter_company_tickers(payload: dict) -> Iterable[dict]:
    # SEC returns either {"0": {...}, "1": {...}} or {"fields": [...], "data": [[...]]}
    if isinstance(payload, dict) and "data" in payload and "fields" in payload:
        fields = payload["fields"]
        for row in payload["data"]:
            yield dict(zip(fields, row))
        return
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, dict):
                yield value


async def fetch_company_tickers(client: SecClient) -> list[dict]:
    payload = await client.get_json(COMPANY_TICKERS_PATH, base="www")
    return list(_iter_company_tickers(payload))


def upsert_companies(db: Session, entries: Iterable[dict]) -> int:
    """Upsert SecCompany rows. Idempotent — returns number of rows touched."""
    count = 0
    for entry in entries:
        cik_raw = entry.get("cik_str") or entry.get("cik")
        ticker = entry.get("ticker")
        name = entry.get("title") or entry.get("name")
        if not cik_raw or not ticker or not name:
            continue
        cik = _pad_cik(str(cik_raw))
        existing: Optional[SecCompany] = db.get(SecCompany, cik)
        if existing is None:
            db.add(
                SecCompany(
                    cik=cik,
                    ticker=ticker.upper(),
                    name=name,
                    exchange=entry.get("exchange"),
                )
            )
        else:
            existing.ticker = ticker.upper()
            existing.name = name
            if entry.get("exchange"):
                existing.exchange = entry["exchange"]
        count += 1
    db.commit()
    return count


async def sync_cik_tickers(db: Session, client: Optional[SecClient] = None) -> int:
    """Fetch SEC company_tickers.json and upsert into sec_companies."""
    owned = False
    if client is None:
        client = SecClient()
        owned = True
    try:
        entries = await fetch_company_tickers(client)
        return upsert_companies(db, entries)
    finally:
        if owned:
            await client.aclose()
