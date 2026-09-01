import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _comparison_model import build_comparison_report  # noqa: E402
from _comparison_report import render_comparison_markdown  # noqa: E402
from _earnings import build_earnings_context  # noqa: E402
from _earnings_analysis import compare_guidance, guidance_vs_actual  # noqa: E402
from _earnings_parser import extract_earnings_release  # noqa: E402
from _earnings_provider import detected_earnings_documents  # noqa: E402
from _earnings_types import EarningsDocument, EarningsRequest  # noqa: E402
from _filing_types import Filing  # noqa: E402
from _report_format import render_markdown  # noqa: E402
from _report_model import build_report  # noqa: E402


@dataclass(frozen=True, slots=True)
class FakeEarningsProvider:
    documents: list[EarningsDocument]
    html: dict[str, str]

    def get_documents(self, _ticker: str, history: int) -> list[EarningsDocument]:
        return self.documents[:history]

    def get_document_text(self, document: EarningsDocument) -> str:
        return self.html[document.source_url]


def test_official_earnings_document_detection_uses_sec_8k_evidence() -> None:
    filings = [
        filing("8-K", "0001", "2026-08-01", "aapl-earnings.htm"),
        filing("10-Q", "0002", "2026-08-02", "aapl-10q.htm"),
        filing("8-K", "0003", "2026-07-01", "aapl-other.htm"),
    ]
    documents = {
        "0001": "Apple reports third quarter results and provides guidance.",
        "0003": "Apple announces debt offering.",
    }

    detected = detected_earnings_documents("AAPL", "Apple Inc.", filings, documents)

    assert [item.document_type for item in detected] == ["earnings_release"]
    assert detected[0].source_type == "SEC_8K"


def test_reported_metric_extraction_keeps_official_evidence() -> None:
    release = extract_earnings_release(document(), earnings_text())

    assert release.reported_metrics["revenue"].value == "100.0"
    assert release.reported_metrics["revenue_growth"].value == "12"
    assert release.reported_metrics["gross_margin"].value == "46"
    assert release.reported_metrics["free_cash_flow"].value == "25.0"
    assert release.reported_metrics["revenue"].source_type == "reported_earnings_metric"


def test_missing_metric_is_not_invented() -> None:
    release = extract_earnings_release(document(), "AAPL reports quarterly results.")

    assert "revenue" not in release.reported_metrics
    assert "GUIDANCE_NOT_PROVIDED" in release.warnings


def test_guidance_range_parsing_and_midpoint() -> None:
    release = extract_earnings_release(document(), earnings_text())
    guidance = release.guidance[0]

    assert guidance.metric == "revenue"
    assert guidance.low == "105.0"
    assert guidance.high == "109.0"
    assert guidance.midpoint == "107.0"


def test_guidance_change_statuses_are_deterministic() -> None:
    previous = guidance("revenue", "next_quarter", "100", "104")

    assert compare_guidance(guidance("revenue", "next_quarter", "110", "114"), previous) == "RAISED"
    assert compare_guidance(guidance("revenue", "next_quarter", "90", "94"), previous) == "LOWERED"
    assert (
        compare_guidance(guidance("revenue", "next_quarter", "100.5", "104.5"), previous)
        == "REITERATED"
    )
    assert (
        compare_guidance(guidance("gross_margin", "next_quarter", "45", "46"), previous)
        == "NOT_COMPARABLE"
    )
    assert (
        compare_guidance(guidance("revenue", "full_year", "100", "104"), previous)
        == "NOT_COMPARABLE"
    )
    assert (
        compare_guidance(
            guidance("revenue", "next_quarter", None, None, status="withdrawn"), previous
        )
        == "WITHDRAWN"
    )
    assert compare_guidance(guidance("revenue", "next_quarter", "110", "114"), None) == "NEW"


def test_previous_guidance_vs_actual_result() -> None:
    actual = extract_earnings_release(document(), earnings_text()).reported_metrics["revenue"]

    assert (
        guidance_vs_actual(guidance("revenue", "current_quarter", "90", "95"), actual)
        == "ABOVE_GUIDANCE"
    )
    assert (
        guidance_vs_actual(guidance("revenue", "current_quarter", "99", "101"), actual)
        == "WITHIN_GUIDANCE"
    )
    assert (
        guidance_vs_actual(guidance("revenue", "current_quarter", "105", "110"), actual)
        == "BELOW_GUIDANCE"
    )
    assert (
        guidance_vs_actual(guidance("gross_margin", "current_quarter", "40", "50"), actual)
        == "NOT_COMPARABLE"
    )


def test_management_statement_extraction_and_change_tracking() -> None:
    provider = FakeEarningsProvider(
        documents=[document("2026-08-01"), previous_document("2026-05-01")],
        html={
            "https://example.com/current": earnings_text(),
            "https://example.com/previous": previous_earnings_text(),
        },
    )

    context = build_earnings_context(EarningsRequest("AAPL", history=2), provider)

    assert context["management_commentary"][0]["category"] == "demand"
    assert (
        context["management_commentary"][0]["evidence"]["source"] == "https://example.com/current"
    )
    assert context["management_tone_changes"][0]["status"] == "IMPROVED"


def test_earnings_change_summary_and_thesis_strengthened() -> None:
    context = build_earnings_context(
        EarningsRequest("AAPL", history=2),
        FakeEarningsProvider(
            [document("2026-08-01"), previous_document("2026-05-01")],
            {
                "https://example.com/current": earnings_text(),
                "https://example.com/previous": previous_earnings_text(),
            },
        ),
    )

    assert any(item["status"] == "RAISED" for item in context["guidance_changes"])
    assert any(item["change_type"] == "guidance_raised" for item in context["changes"])
    assert context["thesis_change"]["status"] == "STRENGTHENED"


def test_thesis_weakened_and_insufficient_evidence() -> None:
    weakened = build_earnings_context(
        EarningsRequest("AAPL", history=2),
        FakeEarningsProvider(
            [document("2026-08-01"), previous_document("2026-05-01")],
            {
                "https://example.com/current": weak_earnings_text(),
                "https://example.com/previous": earnings_text(),
            },
        ),
    )
    insufficient = build_earnings_context(
        EarningsRequest("AAPL"),
        FakeEarningsProvider([], {}),
    )

    assert weakened["thesis_change"]["status"] == "WEAKENED"
    assert insufficient["thesis_change"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_sec_earnings_metric_mismatch_is_reported() -> None:
    context = build_earnings_context(
        EarningsRequest("AAPL", history=1, deterministic_financials={"revenue": "99"}),
        FakeEarningsProvider(
            [document("2026-08-01")], {"https://example.com/current": earnings_text()}
        ),
    )

    assert "EARNINGS_SEC_VALUE_MISMATCH" in context["warnings"]
    assert context["data_quality"]["mismatches"][0]["metric"] == "revenue"


def test_report_localizes_earnings_section_when_context_exists() -> None:
    markdown = render_markdown(
        build_report(
            company(), research_context={"earnings_context": earnings_context()}, language="ko"
        )
    )

    assert "## 최근 실적 변화" in markdown
    assert "| 항목 | 평가 |" in markdown
    assert "투자 논리 변화" in markdown


def test_earnings_comparison_reuses_existing_comparison_report() -> None:
    rows = [
        comparison_row("AMD", "SLIGHTLY_WEAKENED", "LOWERED"),
        comparison_row("NVDA", "STRENGTHENED", "RAISED"),
    ]

    markdown = render_comparison_markdown(build_comparison_report(rows), "en")

    assert "Guidance Change" in markdown
    assert "| Guidance Change | LOWERED | RAISED |" in markdown
    assert "| Thesis Change | SLIGHTLY_WEAKENED | STRENGTHENED |" in markdown


def test_evidence_provenance_is_preserved_in_json() -> None:
    context = build_earnings_context(
        EarningsRequest("AAPL", history=1),
        FakeEarningsProvider(
            [document("2026-08-01")], {"https://example.com/current": earnings_text()}
        ),
    )

    assert context["evidence"][0]["source"] == "https://example.com/current"
    assert context["evidence"][0]["document"] == "Apple reports third quarter results"
    assert context["evidence"][0]["published_at"] == "2026-08-01"


def test_earnings_context_cli_emits_json_when_driven_through_script(tmp_path: Path) -> None:
    fixture = tmp_path / "earnings.json"
    fixture.write_text(json.dumps([document().to_dict()]), encoding="utf-8")
    text = tmp_path / "current.txt"
    text.write_text(earnings_text(), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "earnings_context.py"),
            "AAPL",
            "--fixture-documents",
            str(fixture),
            "--fixture-text-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["version"] == "0.8.0"
    assert payload["latest_earnings"]["document_type"] == "earnings_release"


def document(published_at: str = "2026-08-01") -> EarningsDocument:
    return EarningsDocument(
        ticker="AAPL",
        company="Apple Inc.",
        document_type="earnings_release",
        published_at=published_at,
        period_end="2026-06-30",
        source_url="https://example.com/current",
        source_type="SEC_8K",
        title="Apple reports third quarter results",
        retrieved_at="2026-08-01T00:00:00Z",
    )


def previous_document(published_at: str) -> EarningsDocument:
    return EarningsDocument(
        ticker="AAPL",
        company="Apple Inc.",
        document_type="earnings_release",
        published_at=published_at,
        period_end="2026-03-31",
        source_url="https://example.com/previous",
        source_type="SEC_8K",
        title="Apple reports second quarter results",
        retrieved_at="2026-05-01T00:00:00Z",
    )


def guidance(
    metric: str,
    period: str,
    low: str | None,
    high: str | None,
    *,
    status: str = "reported",
) -> Any:
    from _earnings_types import GuidanceItem

    return GuidanceItem(
        metric=metric,
        period=period,
        low=low,
        high=high,
        midpoint=None,
        unit="USD",
        source="https://example.com/current",
        status=status,
        evidence="guidance evidence",
    )


def filing(form: str, accession: str, filing_date: str, primary_document: str) -> Filing:
    return Filing(
        ticker="AAPL",
        company_name="Apple Inc.",
        form=form,
        filing_date=filing_date,
        period_end="2026-06-30",
        accession_number=accession,
        primary_document=primary_document,
        filing_url=f"https://www.sec.gov/Archives/{accession}/{primary_document}",
        source="https://data.sec.gov/submissions/CIK0000320193.json",
    )


def earnings_text() -> str:
    return (
        "Apple reports third quarter results. Revenue was $100.0 billion, up 12% year over year. "
        "Gross margin was 46%. Operating margin was 32%. Net income was $25.0 billion. "
        "Diluted EPS was $2.50. Operating cash flow was $30.0 billion. "
        "Free cash flow was $25.0 billion. For the next quarter, revenue guidance is "
        "$105.0 billion to $109.0 billion and gross margin guidance is 45% to 46%. "
        "CEO Jane Doe said customer demand improved and supply availability has improved. "
        "Data center segment revenue was $40.0 billion."
    )


def previous_earnings_text() -> str:
    return (
        "Apple reports second quarter results. Revenue was $92.0 billion, up 4% year over year. "
        "Gross margin was 44%. Free cash flow was $15.0 billion. For the next quarter, "
        "revenue guidance is $95.0 billion to $99.0 billion. CEO Jane Doe said supply "
        "remains constrained."
    )


def weak_earnings_text() -> str:
    return (
        "Apple reports third quarter results. Revenue was $80.0 billion, up -5% year over year. "
        "Gross margin was 40%. Free cash flow was $8.0 billion. For the next quarter, "
        "revenue guidance is $70.0 billion to $74.0 billion. CEO Jane Doe said customer "
        "demand weakened."
    )


def company() -> dict[str, Any]:
    return {
        "company": "Apple Inc.",
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
        "current_assets": "900",
        "current_liabilities": "450",
        "inventory": "100",
        "total_assets": "1600",
        "total_liabilities": "500",
        "total_debt": "200",
        "shareholder_equity": "800",
        "book_value_per_share": "20",
        "field_sources": {},
        "market_quote": {"timestamp": "2026-08-28", "provider": "test"},
        "data_quality": {},
        "fact_metadata": {},
        "annuals": [],
    }


def earnings_context() -> dict[str, Any]:
    return {
        "changes": [
            {"change_type": "revenue_acceleration", "status": "IMPROVED"},
            {"change_type": "margin_expansion", "status": "IMPROVED"},
            {"change_type": "fcf_improvement", "status": "IMPROVED"},
        ],
        "guidance_changes": [{"metric": "revenue", "status": "RAISED"}],
        "thesis_change": {"status": "SLIGHTLY_STRENGTHENED"},
        "management_commentary": [{"category": "demand", "statement": "customer demand improved"}],
    }


def comparison_row(ticker: str, thesis: str, guidance_status: str) -> dict[str, Any]:
    result = company()
    result["ticker"] = ticker
    result["company"] = ticker
    result["valuation"] = {"conclusion": "FAIRLY VALUED", "metrics": {}}
    result["financial_quality"] = {"metrics": {}}
    result["risk"] = {"risk_checks": []}
    result["comparison_basis"] = {}
    result["research_context"] = {
        "research_confidence": "MEDIUM",
        "earnings_context": {
            "thesis_change": {"status": thesis},
            "guidance_changes": [{"metric": "revenue", "status": guidance_status}],
            "reported_metrics": {"revenue_growth": {"value": "12"}},
            "evidence": [{"source": "https://example.com/current"}],
        },
    }
    return result
