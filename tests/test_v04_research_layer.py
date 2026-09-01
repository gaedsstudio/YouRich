import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import _research as research_module  # noqa: E402
from _core import ToolError  # noqa: E402
from _evidence import evidence_from_section, linked_claim, unsupported_claim  # noqa: E402
from _filing_parser import clean_filing_html, extract_sections  # noqa: E402
from _filing_provider import FilingQuery, filing_rows  # noqa: E402
from _filing_types import Filing, FilingDocument, FilingSection  # noqa: E402
from _research import build_research_context, risk_factor_change  # noqa: E402
from _research_types import ResearchRequest  # noqa: E402


@dataclass(frozen=True, slots=True)
class FakeFilingProvider:
    filings: list[Filing]
    documents: dict[str, str]

    def get_filings(self, _ticker: str, _forms: list[str], limit: int) -> list[Filing]:
        return self.filings[:limit]

    def get_document(self, filing: Filing) -> FilingDocument:
        return FilingDocument(filing=filing, html=self.documents[filing.accession_number])


def test_filing_rows_returns_sec_metadata_when_recent_payload_contains_forms() -> None:
    recent = {
        "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
        "form": ["8-K", "10-K"],
        "filingDate": ["2026-01-02", "2026-02-03"],
        "reportDate": ["2026-01-01", "2025-12-31"],
        "primaryDocument": ["a.htm", "aapl-20251231.htm"],
    }

    rows = filing_rows(FilingQuery("AAPL", "Apple Inc.", 320193, recent, ["10-K"], 1, "source-url"))

    assert rows[0].to_dict() == {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "form": "10-K",
        "filing_date": "2026-02-03",
        "period_end": "2025-12-31",
        "accession_number": "0000320193-26-000002",
        "primary_document": "aapl-20251231.htm",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019326000002/aapl-20251231.htm",
        "source": "source-url",
    }


def test_filing_rows_prioritizes_latest_filing_per_requested_form() -> None:
    recent = {
        "accessionNumber": ["q2", "q1", "k1"],
        "form": ["10-Q", "10-Q", "10-K"],
        "filingDate": ["2026-08-01", "2026-05-01", "2026-02-01"],
        "reportDate": ["2026-06-30", "2026-03-31", "2025-12-31"],
        "primaryDocument": ["q2.htm", "q1.htm", "k1.htm"],
    }

    rows = filing_rows(
        FilingQuery("AAPL", "Apple Inc.", 320193, recent, ["10-K", "10-Q"], 2, "source")
    )

    assert [row.form for row in rows] == ["10-K", "10-Q"]
    assert [row.accession_number for row in rows] == ["k1", "q2"]


def test_clean_filing_html_removes_noise_when_hidden_xbrl_is_present() -> None:
    raw = (
        "<html><style>x</style><script>bad()</script>"
        "<ix:hidden>secret</ix:hidden><p>Item 1. Business Revenue</p></html>"
    )

    text = clean_filing_html(raw)

    assert "bad" not in text
    assert "secret" not in text
    assert "Item 1. Business Revenue" in text


def test_extract_sections_returns_10k_sections_when_items_are_present() -> None:
    text = sample_10k_text()

    sections, warnings = extract_sections(text, "10-K")

    assert warnings == []
    assert [section.name for section in sections] == [
        "business",
        "risk_factors",
        "properties",
        "legal_proceedings",
        "mda",
        "financial_statements",
        "controls",
    ]


def test_extract_sections_returns_10q_sections_when_quarterly_items_are_present() -> None:
    text = (
        "Item 1. Financial Statements condensed statements.\n"
        "Item 2. Management's Discussion and Analysis liquidity and margins.\n"
        "Item 1A. Risk Factors competition changed.\n"
        "Item 4. Controls and Procedures effective controls."
    )

    sections, warnings = extract_sections(text, "10-Q")

    assert warnings == []
    assert [section.name for section in sections] == [
        "financial_statements",
        "mda",
        "risk_factors",
        "controls",
    ]


def test_extract_sections_handles_curly_apostrophe_in_mda_heading() -> None:
    text = (
        "Item 1. Financial Statements condensed statements.\n"
        "Item 2. Management\u2019s Discussion and Analysis liquidity and margins.\n"
        "Item 1A. Risk Factors competition changed.\n"
        "Item 4. Controls and Procedures effective controls."
    )

    sections, warnings = extract_sections(text, "10-Q")

    assert warnings == []
    assert sections[1].name == "mda"


def test_extract_sections_warns_when_no_known_section_exists() -> None:
    sections, warnings = extract_sections("plain filing text", "10-K")

    assert warnings == ["SECTION_PARSE_INCOMPLETE"]
    assert sections[0].name == "full_filing"


def test_evidence_links_claims_when_section_supports_claim() -> None:
    filing = sample_filing("10-K", "0001", "2026-02-01")
    section = FilingSection("business", "Item 1. Business", "Revenue comes from services.")

    evidence = evidence_from_section(filing, section, "business_model")
    claim = linked_claim("Business model is filing-backed.", "business", [evidence])

    assert evidence.source_url == filing.filing_url
    assert evidence.support_status == "SUPPORTED"
    assert claim.status == "SUPPORTED"
    assert claim.evidence_ids == [evidence.id]


def test_unsupported_claim_keeps_gap_when_evidence_is_absent() -> None:
    claim = unsupported_claim("No moat evidence found.", "moat")

    assert claim.to_dict()["status"] == "INSUFFICIENT_EVIDENCE"
    assert claim.evidence_ids == []


def test_risk_factor_change_is_deterministic_when_text_changes() -> None:
    current = evidence_from_section(
        sample_filing("10-Q", "0002", "2026-05-01"),
        FilingSection(
            "risk_factors", "Item 1A. Risk Factors", "Cybersecurity regulation supply disruption"
        ),
        "qualitative_risk",
    )
    previous = evidence_from_section(
        sample_filing("10-K", "0001", "2026-02-01"),
        FilingSection(
            "risk_factors", "Item 1A. Risk Factors", "Competition currency inflation demand"
        ),
        "qualitative_risk",
    )

    result = risk_factor_change([current, previous])

    assert result["status"] == "CHANGED"
    assert result["evidence_ids"] == [current.id, previous.id]


def test_research_context_builds_compact_evidence_when_filings_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeFilingProvider(
        filings=[
            sample_filing("10-K", "0001", "2026-02-01"),
            sample_filing("10-Q", "0002", "2026-05-01"),
        ],
        documents={"0001": sample_10k_text(), "0002": sample_10q_text()},
    )
    monkeypatch.setattr(research_module, "fetch_financials", fake_financials)

    result = build_research_context(ResearchRequest("AAPL", evidence_limit=8), provider)

    assert result["version"] == "0.6.0"
    assert result["ticker"] == "AAPL"
    assert result["research_confidence"] in {"MEDIUM", "HIGH"}
    assert result["business_analysis"]["segments"]["status"] == "SUPPORTED"
    assert result["business_analysis"]["recurring_vs_transactional"]["status"] == "SUPPORTED"
    assert len(result["evidence"]) <= 8
    assert result["risk_analysis"]["quantitative_risk"] is not None


def test_research_context_reports_financial_gap_when_financial_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeFilingProvider(
        filings=[sample_filing("10-K", "0001", "2026-02-01")],
        documents={"0001": sample_10k_text()},
    )
    monkeypatch.setattr(research_module, "fetch_financials", fake_financial_failure)

    result = build_research_context(ResearchRequest("AAPL"), provider)

    assert result["mda_cross_check"]["status"] == "INSUFFICIENT_DATA"
    assert any(str(item).startswith("FINANCIAL_DATA_PARTIAL") for item in result["warnings"])


def test_filing_parser_cli_emits_sections_when_driven_through_script() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "filing_parser.py"), "--form", "10-K"],
        input=sample_10k_text(),
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(completed.stdout)

    assert payload["warnings"] == []
    assert payload["sections"][0]["name"] == "business"


def fake_financials(_ticker: str) -> dict[str, Any]:
    return {
        "ticker": "AAPL",
        "current_price": "20",
        "market_cap": "2000",
        "shares_outstanding": "100",
        "revenue": "1000",
        "gross_profit": "500",
        "operating_income": "250",
        "net_income": "200",
        "eps": "2",
        "free_cash_flow": "150",
        "cash": "100",
        "current_assets": "900",
        "current_liabilities": "450",
        "inventory": "100",
        "total_assets": "1600",
        "total_liabilities": "500",
        "total_debt": "200",
        "shareholder_equity": "800",
        "book_value_per_share": "20",
        "field_sources": {},
        "fact_metadata": {},
        "provider": {"warnings": []},
        "annuals": [],
    }


def fake_financial_failure(_ticker: str) -> dict[str, Any]:
    raise ToolError("offline")


def sample_filing(form: str, accession: str, filing_date: str) -> Filing:
    return Filing(
        ticker="AAPL",
        company_name="Apple Inc.",
        form=form,
        filing_date=filing_date,
        period_end="2025-12-31",
        accession_number=accession,
        primary_document="aapl.htm",
        filing_url=f"https://www.sec.gov/Archives/{accession}/aapl.htm",
        source="https://data.sec.gov/submissions/CIK0000320193.json",
    )


def sample_10k_text() -> str:
    return (
        "Item 1. Business Revenue comes from products, services, subscription sales, "
        "segments, international geography, customers, cost structure, capital "
        "expenditure, competition, suppliers.\n"
        "Item 1A. Risk Factors Competition, regulation, demand, supply, and "
        "cybersecurity could affect results.\n"
        "Item 2. Properties Stores, data centers, and equipment.\n"
        "Item 3. Legal Proceedings Routine litigation.\n"
        "Item 7. Management's Discussion and Analysis Revenue growth, margins, "
        "liquidity, capital allocation, repurchase, dividend, and acquisition activity.\n"
        "Item 8. Financial Statements Consolidated statements.\n"
        "Item 9A. Controls and Procedures Disclosure controls."
    )


def sample_10q_text() -> str:
    return (
        "Item 1. Financial Statements Condensed consolidated statements.\n"
        "Item 2. Management's Discussion and Analysis Revenue growth, margins, liquidity, "
        "repurchase, dividend, acquisition, and capital allocation.\n"
        "Item 1A. Risk Factors Competition, regulation, demand, supply, and "
        "cybersecurity could affect results.\n"
        "Item 4. Controls and Procedures Disclosure controls."
    )
