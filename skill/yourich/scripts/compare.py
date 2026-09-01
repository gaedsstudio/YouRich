import argparse
from typing import Any

from _comparison_report import render_comparison_markdown
from _core import ToolError, write_json
from _research import build_research_context, parse_research_request
from _sec import fetch_financials
from financial_health import financial_health
from risk import risk_checks
from valuation import valuation

MIN_COMPARE_ARGS = 3
MIN_COMPARE_ROWS = 2


def compare(tickers: list[str], include_research: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        company = fetch_financials(ticker)
        valuation_result = valuation(company)
        row = {
            "company": company["company"],
            "ticker": company["ticker"],
            "valuation": valuation_result,
            "financial_quality": financial_health(company),
            "risk": risk_checks(company),
            "missing_fields": company["missing_fields"],
            "provider": company["provider"],
            "comparison_basis": comparison_basis(valuation_result),
        }
        if include_research:
            row["research_context"] = build_research_context(
                parse_research_request(ticker, "thesis", 2, 12)
            )
        rows.append(row)
    warnings = comparison_warnings(rows)
    if warnings:
        for row in rows:
            row["comparison_warnings"] = warnings
    return rows


def comparison_basis(valuation_result: dict[str, Any]) -> dict[str, str | None]:
    metrics = valuation_result.get("metrics")
    if not isinstance(metrics, dict):
        return {}
    return {name: metric_basis(metrics, name) for name in ("pe", "ps", "fcf_yield", "pb")}


def metric_basis(metrics: dict[Any, Any], name: str) -> str | None:
    metric = metrics.get(name)
    if not isinstance(metric, dict):
        return None
    periods = metric.get("periods")
    if not isinstance(periods, dict):
        return None
    return "|".join(str(value) for key, value in sorted(periods.items()) if key.endswith("_basis"))


def comparison_warnings(rows: list[dict[str, Any]]) -> list[str]:
    if len(rows) < MIN_COMPARE_ROWS:
        return []
    first = rows[0].get("comparison_basis")
    if not isinstance(first, dict):
        return []
    warnings = []
    for metric in ("pe", "ps", "fcf_yield", "pb"):
        expected = first.get(metric)
        if any(metric_basis_differs(row, metric, expected) for row in rows[1:]):
            warnings.append(f"NOT_COMPARABLE:{metric}")
    return warnings


def metric_basis_differs(row: dict[str, Any], metric: str, expected: Any) -> bool:
    basis = row.get("comparison_basis")
    return isinstance(basis, dict) and basis.get(metric) != expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--language", choices=("en", "ko"), default="en")
    args = parser.parse_args()
    try:
        if len(args.tickers) < MIN_COMPARE_ARGS - 1:
            raise ToolError("compare requires at least two tickers")
        rows = compare(args.tickers, include_research=args.format == "markdown")
        if args.format == "markdown":
            print(render_comparison_markdown(rows, args.language), end="")
        else:
            write_json(rows)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
