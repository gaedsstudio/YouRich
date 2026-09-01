import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _comparison_model import build_comparison_report  # noqa: E402
from _comparison_report import render_comparison_markdown  # noqa: E402


def test_business_comparison_uses_research_evidence_when_supplied() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")

    assert "데이터센터와 AI 가속기 수요가 매출 성장을 이끌고 있습니다." in markdown
    assert "CUDA 생태계와 데이터센터 플랫폼 수요가 경쟁 우위를 뒷받침합니다." in markdown
    assert "사업 근거 | 근거가 부족합니다." not in markdown
    assert "근거가 부족합니다." not in section(markdown, "## 사업 경쟁력", "## 재무 상태")


def test_business_evidence_skips_sec_item_headings() -> None:
    rows = [
        comparison_row(
            "AAA",
            research_context=research_context(
                "AAA",
                "ITEM 1. Business. Platform revenue is supported by long-term contracts.",
                "MEDIUM",
                "INSUFFICIENT_EVIDENCE",
                "ITEM 1A. Risk Factors. Customer concentration can pressure results.",
            ),
        ),
        comparison_row("BBB"),
    ]

    markdown = render_comparison_markdown(build_comparison_report(rows), "en")

    assert "ITEM 1." not in markdown
    assert "Platform revenue is supported by long-term contracts." in markdown
    assert "Customer concentration can pressure results." in markdown


def test_business_evidence_skips_table_of_contents_fragments() -> None:
    rows = [
        comparison_row(
            "AAA",
            research_context=research_context(
                "AAA",
                "Business 1. Platform revenue is supported by long-term contracts.",
                "MEDIUM",
                "INSUFFICIENT_EVIDENCE",
                "Risk Factors 14 ITEM 1B. Customer concentration can pressure results.",
            ),
        ),
        comparison_row("BBB"),
    ]

    markdown = render_comparison_markdown(build_comparison_report(rows), "en")

    assert "Business 1." not in markdown
    assert "Risk Factors 14" not in markdown
    assert "Platform revenue is supported by long-term contracts." in markdown
    assert "Customer concentration can pressure results." in markdown


def test_business_comparison_prefers_specific_business_topics() -> None:
    context = research_context(
        "AAA",
        "The statements in this report include forward-looking statements.",
        "MEDIUM",
        "INSUFFICIENT_EVIDENCE",
        "Competition can pressure results.",
    )
    context["evidence"].append(
        {
            "claim_type": "industry_position",
            "excerpt": "AAA is positioned across cloud, edge, embedded, and end devices.",
        }
    )

    markdown = render_comparison_markdown(
        build_comparison_report(
            [comparison_row("AAA", research_context=context), comparison_row("BBB")]
        ),
        "en",
    )

    assert "AAA is positioned across cloud, edge, embedded, and end devices." in markdown
    assert "forward-looking statements" not in section(
        markdown, "## Business Quality", "## Financial Quality"
    )


def test_business_fallback_appears_only_without_evidence() -> None:
    first = comparison_row("AAA")
    second = comparison_row("BBB")

    markdown = render_comparison_markdown(build_comparison_report([first, second]), "ko")

    assert "| AAA | BBB |" in markdown
    assert "근거가 부족합니다." in section(markdown, "## 사업 경쟁력", "## 재무 상태")


def test_key_differences_change_with_supplied_metrics() -> None:
    first = comparison_row("AMD", net_margin="12", fcf_margin="8", pe="70", fcf_yield="1")
    second = comparison_row("NVDA", net_margin="55", fcf_margin="40", pe="35", fcf_yield="3")

    markdown = render_comparison_markdown(build_comparison_report([first, second]), "ko")
    differences = section(markdown, "## 핵심 차이", "## 사업 경쟁력")

    assert "NVDA는 순이익률에서 AMD보다 앞섭니다." in differences
    assert "NVDA는 잉여현금흐름 마진에서 AMD보다 앞섭니다." in differences
    assert "AMD는 P/E 부담이 NVDA보다 높습니다." in differences


def test_amd_nvidia_like_fixture_creates_different_company_conclusions() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")

    assert "| 결론 | EXPENSIVE | FAIRLY VALUED |" in markdown


def test_bull_case_is_company_specific() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")

    amd = section(markdown, "## AMD 상승 / 하락 시나리오", "## NVDA 상승 / 하락 시나리오")
    nvda = section(markdown, "## NVDA 상승 / 하락 시나리오", "## 결론")
    assert "데이터센터와 AI 가속기 수요" in amd
    assert "CUDA 생태계" in nvda
    assert amd != nvda


def test_bear_case_is_company_specific() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")

    amd = section(markdown, "## AMD 상승 / 하락 시나리오", "## NVDA 상승 / 하락 시나리오")
    nvda = section(markdown, "## NVDA 상승 / 하락 시나리오", "## 결론")
    assert "가치평가 위험" in amd
    assert "공급 제약과 고객 집중 위험" in nvda
    assert amd != nvda


def test_comparison_conclusion_contains_evidence_without_action_instruction() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")
    conclusion = section(markdown, "## 결론", "## 데이터 및 산출 기준")

    assert "NVDA는 순이익률에서 AMD보다 앞섭니다." in conclusion
    assert "사업 경쟁력 근거가 더 강합니다." in conclusion
    assert "사라" not in conclusion
    assert "매수" not in conclusion
    assert "매도" not in conclusion


def test_evidence_quality_comes_from_research_coverage() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")

    assert "| 근거 품질 | MEDIUM | HIGH |" in markdown


def test_what_changed_uses_filing_delta_data_when_supplied() -> None:
    rows = comparison_rows_with_research()

    markdown = render_comparison_markdown(build_comparison_report(rows), "ko")
    methodology = section(markdown, "## 데이터 및 산출 기준", "")

    assert "최근 변화" in methodology
    assert "AMD: 위험 요인 문구 변화가 감지되었습니다." in methodology
    assert "NVDA: 위험 요인 문구 변화가 감지되지 않았습니다." in methodology


def test_english_comparison_output_preserves_section_order() -> None:
    markdown = render_comparison_markdown(
        build_comparison_report(comparison_rows_with_research()), "en"
    )
    headings = [
        line.removeprefix("## ") for line in markdown.splitlines() if line.startswith("## ")
    ]

    assert headings == [
        "Overall Comparison",
        "Key Differences",
        "Business Quality",
        "Financial Quality",
        "Valuation",
        "Key Risks",
        "AMD Bull / Bear Case",
        "NVDA Bull / Bear Case",
        "Conclusion",
        "Data Quality & Methodology",
    ]


def comparison_rows_with_research() -> list[dict[str, Any]]:
    return [
        comparison_row(
            "AMD",
            net_margin="12",
            fcf_margin="8",
            pe="70",
            fcf_yield="1",
            conclusion="EXPENSIVE",
            research_context=research_context(
                "AMD",
                "데이터센터와 AI 가속기 수요가 매출 성장을 이끌고 있습니다.",
                "MEDIUM",
                "CHANGED",
                "AI 성장 기대 둔화와 경쟁 심화가 주요 위험입니다.",
            ),
        ),
        comparison_row(
            "NVDA",
            net_margin="55",
            fcf_margin="40",
            pe="35",
            fcf_yield="3",
            conclusion="FAIRLY VALUED",
            research_context=research_context(
                "NVDA",
                "CUDA 생태계와 데이터센터 플랫폼 수요가 경쟁 우위를 뒷받침합니다.",
                "HIGH",
                "NO_MATERIAL_TEXT_CHANGE",
                "공급 제약과 고객 집중 위험을 공시에서 설명합니다.",
            ),
        ),
    ]


def comparison_row(
    ticker: str,
    *,
    net_margin: str = "20",
    fcf_margin: str = "10",
    pe: str = "30",
    fcf_yield: str = "2",
    conclusion: str = "FAIRLY VALUED",
    research_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "company": ticker,
        "ticker": ticker,
        "valuation": {
            "conclusion": conclusion,
            "metrics": {
                "pe": {"value": Decimal(pe), "basis": "ttm"},
                "fcf_yield": {"value": Decimal(fcf_yield), "basis": "ttm"},
            },
        },
        "financial_quality": {
            "metrics": {
                "net_margin": {"value": Decimal(net_margin)},
                "fcf_margin": {"value": Decimal(fcf_margin)},
            },
        },
        "risk": {
            "risk_checks": [{"id": "valuation_risk", "status": "triggered", "severity": "low"}]
        },
        "comparison_basis": {"pe": "ttm|market_quote"},
        "research_context": research_context,
    }


def research_context(
    ticker: str,
    business_excerpt: str,
    confidence: str,
    change_status: str,
    risk_excerpt: str,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "research_confidence": confidence,
        "evidence_coverage": {"business": confidence, "risk": "MEDIUM"},
        "evidence": [
            {"claim_type": "business_model", "excerpt": business_excerpt},
            {"claim_type": "qualitative_risk", "excerpt": risk_excerpt},
        ],
        "risk_analysis": {"risk_factor_change": {"status": change_status}},
    }


def section(markdown: str, start: str, end: str) -> str:
    start_index = markdown.index(start)
    if not end:
        return markdown[start_index:]
    return markdown[start_index : markdown.index(end, start_index)]
