"""Form 4 XML parser. Uses defusedxml to defuse XXE / billion-laughs attacks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from defusedxml import ElementTree as ET


@dataclass
class Form4Transaction:
    issuer_cik: Optional[str] = None
    issuer_ticker: Optional[str] = None
    insider_name: str = ""
    insider_cik: Optional[str] = None
    relationship_type: Optional[str] = None
    transaction_date: Optional[date] = None
    transaction_code: Optional[str] = None
    security_title: Optional[str] = None
    shares: Optional[float] = None
    price_per_share: Optional[float] = None
    acquired_disposed_code: Optional[str] = None
    shares_owned_following: Optional[float] = None
    is_derivative: bool = False


def _text(node, path: str) -> Optional[str]:
    if node is None:
        return None
    found = node.find(path)
    if found is None or found.text is None:
        return None
    text = found.text.strip()
    return text or None


def _float(node, path: str) -> Optional[float]:
    raw = _text(node, path)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _pad_cik(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits:
        return None
    return digits.zfill(10)


def _relationship(reporting_owner) -> Optional[str]:
    if reporting_owner is None:
        return None
    rel = reporting_owner.find("reportingOwnerRelationship")
    if rel is None:
        return None
    flags = []
    if _text(rel, "isDirector") == "1":
        flags.append("Director")
    if _text(rel, "isOfficer") == "1":
        flags.append("Officer")
    if _text(rel, "isTenPercentOwner") == "1":
        flags.append("10% Owner")
    if _text(rel, "isOther") == "1":
        flags.append("Other")
    title = _text(rel, "officerTitle")
    if title:
        flags.append(title)
    return ", ".join(flags) if flags else None


def parse_form4_xml(xml_content: str | bytes) -> List[Form4Transaction]:
    """Parse a Form 4 ownershipDocument XML payload. Returns one entry per transaction.

    Uses defusedxml.ElementTree.fromstring — never use stdlib xml.etree directly here.
    """
    if isinstance(xml_content, bytes):
        root = ET.fromstring(xml_content)
    else:
        root = ET.fromstring(xml_content)

    issuer = root.find("issuer")
    issuer_cik = _pad_cik(_text(issuer, "issuerCik"))
    issuer_ticker = _text(issuer, "issuerTradingSymbol")

    reporting_owner = root.find("reportingOwner")
    if reporting_owner is None:
        owner_id = None
        owner_name = ""
        owner_cik = None
    else:
        owner_id = reporting_owner.find("reportingOwnerId")
        owner_name = _text(owner_id, "rptOwnerName") or ""
        owner_cik = _pad_cik(_text(owner_id, "rptOwnerCik"))
    relationship_type = _relationship(reporting_owner)

    transactions: List[Form4Transaction] = []

    for txn in root.iter("nonDerivativeTransaction"):
        transactions.append(_parse_txn(
            txn,
            issuer_cik=issuer_cik,
            issuer_ticker=issuer_ticker,
            owner_name=owner_name,
            owner_cik=owner_cik,
            relationship_type=relationship_type,
            is_derivative=False,
        ))

    for txn in root.iter("derivativeTransaction"):
        transactions.append(_parse_txn(
            txn,
            issuer_cik=issuer_cik,
            issuer_ticker=issuer_ticker,
            owner_name=owner_name,
            owner_cik=owner_cik,
            relationship_type=relationship_type,
            is_derivative=True,
        ))

    return transactions


def _parse_txn(
    txn,
    *,
    issuer_cik: Optional[str],
    issuer_ticker: Optional[str],
    owner_name: str,
    owner_cik: Optional[str],
    relationship_type: Optional[str],
    is_derivative: bool,
) -> Form4Transaction:
    return Form4Transaction(
        issuer_cik=issuer_cik,
        issuer_ticker=issuer_ticker,
        insider_name=owner_name,
        insider_cik=owner_cik,
        relationship_type=relationship_type,
        transaction_date=_parse_date(_text(txn, "transactionDate/value")),
        transaction_code=_text(txn, "transactionCoding/transactionCode"),
        security_title=_text(txn, "securityTitle/value"),
        shares=_float(txn, "transactionAmounts/transactionShares/value"),
        price_per_share=_float(txn, "transactionAmounts/transactionPricePerShare/value"),
        acquired_disposed_code=_text(
            txn, "transactionAmounts/transactionAcquiredDisposedCode/value"
        ),
        shares_owned_following=_float(
            txn, "postTransactionAmounts/sharesOwnedFollowingTransaction/value"
        ),
        is_derivative=is_derivative,
    )
