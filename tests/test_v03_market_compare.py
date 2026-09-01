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
