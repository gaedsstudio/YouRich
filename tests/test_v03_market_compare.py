import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _core  # noqa: E402
import _market  # noqa: E402
import compare as compare_module  # noqa: E402
from _comparison_report import render_comparison_markdown  # noqa: E402
from v03_fixtures import valuation_payload  # noqa: E402


def test_market_provider_fallback_and_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FailingProvider:
        def get_quote(self, ticker: str) -> _market.MarketQuote:
            raise _core.ToolError(f"failed {ticker}")

    class WorkingProvider:
        def get_quote(self, ticker: str) -> _market.MarketQuote:
            return _market.MarketQuote(
                ticker=ticker,
                price=Decimal("10"),
                currency="USD",
                timestamp="2026-08-28",
                source="source",
                is_delayed=True,
                provider="test",
            )

    monkeypatch.setattr(
        _market, "configured_providers", lambda: [FailingProvider(), WorkingProvider()]
    )
    monkeypatch.setenv("YOURICH_CACHE_DIR", str(tmp_path))

    quote, warnings = _market.get_market_quote("AAPL")
    assert quote is not None
    assert quote["price"] == Decimal("10")
    assert warnings == ["failed AAPL"]
    assert cache_round_trip(tmp_path) == ({"calls": 1}, {"calls": 1}, {"calls": 2})


def test_compare_marks_different_basis_as_not_comparable(monkeypatch: pytest.MonkeyPatch) -> None:
    first = valuation_payload()
    second = valuation_payload()
    second["fact_metadata"]["revenue"]["basis"] = "latest_annual"

    def fake_fetch_financials(ticker: str) -> dict[str, Any]:
        return first if ticker == "AAA" else second

    monkeypatch.setattr(compare_module, "fetch_financials", fake_fetch_financials)

    rows = compare_module.compare(["AAA", "BBB"])

    assert rows[0]["comparison_warnings"] == ["NOT_COMPARABLE:ps"]


def test_comparison_report_preserves_section_order(monkeypatch: pytest.MonkeyPatch) -> None:
    first = valuation_payload()
    second = valuation_payload()
    first["ticker"] = "AAA"
    second["company"] = "Second Co"
    second["ticker"] = "BBB"

    def fake_fetch_financials(ticker: str) -> dict[str, Any]:
        return first if ticker == "AAA" else second

    monkeypatch.setattr(compare_module, "fetch_financials", fake_fetch_financials)

    markdown = render_comparison_markdown(compare_module.compare(["AAA", "BBB"]), "ko")
    headings = [
        line.removeprefix("## ") for line in markdown.splitlines() if line.startswith("## ")
    ]

    assert headings == [
        "종합 비교",
        "핵심 차이",
        "사업 경쟁력",
        "재무 상태",
        "가치평가",
        "주요 위험",
        "AAA 상승 / 하락 시나리오",
        "BBB 상승 / 하락 시나리오",
        "결론",
        "데이터 및 산출 기준",
    ]


def test_comparison_report_renders_main_table(monkeypatch: pytest.MonkeyPatch) -> None:
    first = valuation_payload()
    second = valuation_payload()
    first["ticker"] = "AAA"
    second["company"] = "Second Co"
    second["ticker"] = "BBB"

    def fake_fetch_financials(ticker: str) -> dict[str, Any]:
        return first if ticker == "AAA" else second

    monkeypatch.setattr(compare_module, "fetch_financials", fake_fetch_financials)

    markdown = render_comparison_markdown(compare_module.compare(["AAA", "BBB"]), "ko")

    assert markdown.startswith("# AAA vs BBB")
    assert "| 항목 | AAA | BBB |" in markdown
    assert "P/E(주가수익비율)" in markdown
    assert "잉여현금흐름 수익률" in markdown


def test_comparison_report_humanizes_korean_risk_and_basis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = valuation_payload()
    second = valuation_payload()
    first["ticker"] = "AAA"
    second["ticker"] = "BBB"
    first["current_price"] = "100"
    first["market_cap"] = "10000"

    def fake_fetch_financials(ticker: str) -> dict[str, Any]:
        return first if ticker == "AAA" else second

    monkeypatch.setattr(compare_module, "fetch_financials", fake_fetch_financials)

    markdown = render_comparison_markdown(compare_module.compare(["AAA", "BBB"]), "ko")

    assert "가치평가 위험" in markdown
    assert "latest_annual" not in markdown
    assert "market_quote" not in markdown
    assert "최근 12개월 + 시장 가격" in markdown


def cache_round_trip(tmp_path: Path) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    calls = 0
    os.environ["YOURICH_CACHE_DIR"] = str(tmp_path)

    def loader() -> dict[str, int]:
        nonlocal calls
        calls += 1
        return {"calls": calls}

    first = _core.cached_json("unit/cache", 1_000, loader)
    second = _core.cached_json("unit/cache", 1_000, loader)
    path = _core.cache_path("unit/cache")
    stale_time = time.time() - 2_000
    os.utime(path, (stale_time, stale_time))
    third = _core.cached_json("unit/cache", 1_000, loader)
    return first, second, third
