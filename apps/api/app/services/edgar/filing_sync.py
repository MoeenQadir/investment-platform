"""Sync recent SEC filings (10-K, 10-Q, 8-K, 4) for a CIK."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import SecFiling
from app.services.edgar.sec_client import SecClient


DEFAULT_FORM_TYPES = {"10-K", "10-Q", "8-K", "4"}


def _pad_cik(cik: str) -> str:
    return str(cik).strip().zfill(10)


def _submissions_path(cik: str) -> str:
    return f"/submissions/CIK{_pad_cik(cik)}.json"


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_datetime(date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    fmt_date = "%Y-%m-%d"
    if time_str:
        try:
            return datetime.strptime(f"{date_str} {time_str}", f"{fmt_date} %H:%M:%S")
        except ValueError:
            pass
    try:
        return datetime.strptime(date_str, fmt_date)
    except ValueError:
        return None


def _build_index_url(cik: str, accession_no: str) -> str:
    acc_nodash = accession_no.replace("-", "")
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={_pad_cik(cik)}&type=&dateb=&owner=include&count=40#{acc_nodash}"


def _build_primary_doc_url(cik: str, accession_no: str, primary_doc: Optional[str]) -> Optional[str]:
    if not primary_doc:
        return None
    acc_nodash = accession_no.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{primary_doc}"


def iter_recent_filings(submissions: dict) -> Iterable[dict]:
    recent = submissions.get("filings", {}).get("recent", {})
    if not recent:
        return
    keys = [
        "accessionNumber",
        "form",
        "filingDate",
        "acceptanceDateTime",
        "reportDate",
        "primaryDocument",
    ]
    columns = [recent.get(k, []) for k in keys]
    if not columns[0]:
        return
    length = len(columns[0])
    for i in range(length):
        yield {
            "accessionNumber": columns[0][i] if i < len(columns[0]) else None,
            "form": columns[1][i] if i < len(columns[1]) else None,
            "filingDate": columns[2][i] if i < len(columns[2]) else None,
            "acceptanceDateTime": columns[3][i] if i < len(columns[3]) else None,
            "reportDate": columns[4][i] if i < len(columns[4]) else None,
            "primaryDocument": columns[5][i] if i < len(columns[5]) else None,
        }


def insert_filings(
    db: Session,
    cik: str,
    entries: Iterable[dict],
    form_types: Optional[set[str]] = None,
) -> int:
    """Insert filings, skipping rows whose accession_no already exists."""
    allowed = form_types if form_types is not None else DEFAULT_FORM_TYPES
    cik_padded = _pad_cik(cik)
    inserted = 0
    for entry in entries:
        accession_no = entry.get("accessionNumber")
        form_type = entry.get("form")
        if not accession_no or not form_type:
            continue
        if allowed and form_type not in allowed:
            continue
        filed_at = _parse_datetime(entry.get("filingDate"), None)
        accepted = entry.get("acceptanceDateTime")
        if accepted:
            try:
                filed_at = datetime.fromisoformat(accepted.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                pass
        if filed_at is None:
            continue

        exists = (
            db.query(SecFiling.id)
            .filter(SecFiling.accession_no == accession_no)
            .first()
        )
        if exists is not None:
            continue

        filing = SecFiling(
            cik=cik_padded,
            accession_no=accession_no,
            form_type=form_type,
            filed_at=filed_at,
            period_of_report=_parse_date(entry.get("reportDate")),
            primary_doc_url=_build_primary_doc_url(
                cik_padded, accession_no, entry.get("primaryDocument")
            ),
            filing_index_url=_build_index_url(cik_padded, accession_no),
        )
        db.add(filing)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        inserted += 1
    db.commit()
    return inserted


async def sync_filings_for_cik(
    db: Session,
    cik: str,
    client: Optional[SecClient] = None,
    form_types: Optional[set[str]] = None,
) -> int:
    """Fetch SEC submissions for a CIK and insert new filings."""
    owned = False
    if client is None:
        client = SecClient()
        owned = True
    try:
        payload = await client.get_json(_submissions_path(cik), base="data")
        entries = list(iter_recent_filings(payload))
        return insert_filings(db, cik, entries, form_types=form_types)
    finally:
        if owned:
            await client.aclose()
