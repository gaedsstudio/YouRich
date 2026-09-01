import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _event_timeline import build_event_intelligence  # noqa: E402
from _report_format import render_markdown  # noqa: E402
from _report_model import build_report  # noqa: E402
from _tracking_report import render_tracking_markdown  # noqa: E402
from v09_event_fixtures import event_input, filing, run_event_cli, run_event_cli_text  # noqa: E402


def test_report_and_tracking_integration_are_explicit_only() -> None:
    event_context = build_event_intelligence(event_input(filing("Revenue guidance was raised.")))
    plain = render_markdown(build_report(report_company()))
    event_report = render_markdown(
        build_report(report_company(), event_context=event_context, language="ko")
    )
    tracking = render_tracking_markdown(
        {"status": "CHANGED", "changes": [], "event_context": event_context}, "ko"
    )

    assert "주요 최근 이벤트" not in plain
    assert "주요 최근 이벤트" in event_report
    assert "새로운 주요 이벤트" in tracking


def test_event_cli_json_and_markdown(tmp_path: Path) -> None:
    payload = event_input(filing("Revenue guidance was raised.", accession="cli"))

    json_result = run_event_cli(tmp_path, payload, "NVDA", "--format", "json")
    markdown = run_event_cli_text(
        tmp_path, payload, "NVDA", "--format", "markdown", "--language", "ko"
    )

    assert json_result["version"] == "0.9.0"
    assert json_result["material_events"][0]["event_type"] == "GUIDANCE_CHANGE"
    assert "핵심 이벤트" in markdown


def report_company() -> dict[str, Any]:
    return {
        "company": "NVIDIA Corporation",
        "ticker": "NVDA",
        "current_price": "100",
        "market_cap": "10000",
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
        "book_value_per_share": "8",
        "field_sources": {},
        "market_quote": {"timestamp": "2026-08-28", "provider": "test"},
        "data_quality": {},
        "fact_metadata": {},
        "annuals": [],
    }
