"""Tests for app.services.edgar.form4_parser."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.services.edgar.form4_parser import parse_form4_xml


FIXTURE = Path(__file__).parent / "fixtures" / "form4_sample.xml"


def test_parses_all_transactions():
    xml = FIXTURE.read_text()
    txns = parse_form4_xml(xml)
    assert len(txns) == 3  # 2 non-derivative + 1 derivative


def test_issuer_and_owner_fields():
    txns = parse_form4_xml(FIXTURE.read_text())
    first = txns[0]
    assert first.issuer_cik == "0000320193"
    assert first.issuer_ticker == "AAPL"
    assert first.insider_name == "COOK TIMOTHY D"
    assert first.insider_cik == "0001214156"
    assert "Director" in (first.relationship_type or "")
    assert "Officer" in (first.relationship_type or "")
    assert "Chief Executive Officer" in (first.relationship_type or "")


def test_non_derivative_sale_transaction():
    txns = parse_form4_xml(FIXTURE.read_text())
    sale = next(t for t in txns if not t.is_derivative and t.transaction_code == "S")
    assert sale.transaction_date == date(2026, 5, 10)
    assert sale.shares == 50000.0
    assert sale.price_per_share == 185.42
    assert sale.acquired_disposed_code == "D"
    assert sale.shares_owned_following == 3200000.0
    assert sale.security_title == "Common Stock"


def test_non_derivative_purchase_transaction():
    txns = parse_form4_xml(FIXTURE.read_text())
    buy = next(t for t in txns if not t.is_derivative and t.transaction_code == "P")
    assert buy.shares == 1000.0
    assert buy.price_per_share == 180.0
    assert buy.acquired_disposed_code == "A"


def test_derivative_transaction_flagged():
    txns = parse_form4_xml(FIXTURE.read_text())
    deriv = [t for t in txns if t.is_derivative]
    assert len(deriv) == 1
    assert deriv[0].security_title == "Restricted Stock Unit"
    assert deriv[0].transaction_code == "M"
    assert deriv[0].transaction_date == date(2026, 5, 9)


def test_accepts_bytes_input():
    txns = parse_form4_xml(FIXTURE.read_bytes())
    assert len(txns) == 3


def test_uses_defusedxml_module():
    """Guard against accidental switch to stdlib xml.etree."""
    from app.services.edgar import form4_parser

    assert form4_parser.ET.__name__ == "defusedxml.ElementTree"


def test_rejects_xxe_doctype_payload():
    """XXE payload must raise — defusedxml blocks DOCTYPE/external entities."""
    import pytest
    from defusedxml.common import DefusedXmlException

    xxe = b"""<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<ownershipDocument>
  <issuer>
    <issuerCik>0000320193</issuerCik>
    <issuerTradingSymbol>&xxe;</issuerTradingSymbol>
  </issuer>
</ownershipDocument>"""
    with pytest.raises(DefusedXmlException):
        parse_form4_xml(xxe)


def test_rejects_entity_expansion_payload():
    """Billion-laughs style entity expansion must raise."""
    import pytest
    from defusedxml.common import DefusedXmlException

    billion_laughs = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<ownershipDocument><x>&lol3;</x></ownershipDocument>"""
    with pytest.raises(DefusedXmlException):
        parse_form4_xml(billion_laughs)
