from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any

from _core import ToolError, clean_ticker, read_payload, write_json
from _report_format import pct
from _sec import fetch_financials
from _valuation_intelligence import build_valuation_intelligence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", nargs="?")
    parser.add_argument("--input")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--discount-rate", default="10")
    parser.add_argument("--terminal-growth", default="3")
    parser.add_argument("--forecast-years", type=int, default=5)
    parser.add_argument("--bear-growth")
    parser.add_argument("--base-growth")
    parser.add_argument("--bull-growth")
    args = parser.parse_args()
    try:
        company = load_company(args)
        result = build_valuation_intelligence(
            company,
            forecast_years=args.forecast_years,
            discount_rate=args.discount_rate,
            terminal_growth=args.terminal_growth,
            growth_overrides=growth_overrides(args),
        )
        if args.format == "markdown":
            print(render_markdown(result), end="")
        else:
            write_json(result)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


def load_company(args: argparse.Namespace) -> dict[str, Any]:
    if args.input and args.ticker:
        raise ToolError("use either --input or ticker, not both")
    if args.input:
        return read_payload(args.input)
    if args.ticker:
        return fetch_financials(clean_ticker(args.ticker))
    raise ToolError("ticker or --input is required")


def growth_overrides(args: argparse.Namespace) -> dict[str, Decimal] | None:
    values = {
        "bear": args.bear_growth,
        "base": args.base_growth,
        "bull": args.bull_growth,
    }
    parsed = {key: Decimal(str(value)) for key, value in values.items() if value is not None}
    return parsed or None


def render_markdown(result: dict[str, Any]) -> str:
    reverse = result["reverse_dcf"]
    margin = result["margin_of_safety"]
    lines = [
        f"# {result.get('ticker')} Valuation Intelligence",
        "",
        "## Current Valuation",
        f"- Reverse DCF status: {reverse.get('status')}",
        f"- Required FCF growth: {pct(reverse.get('required_fcf_cagr'))}",
        "",
        "## Scenarios",
    ]
    lines.extend(
        [
            (
                f"- {scenario.get('scenario', '').title()}: {scenario.get('value_range')} "
                f"({scenario.get('position')})"
            )
            for scenario in result["scenarios"]
        ]
    )
    lines.extend(
        [
            "",
            "## Scenario Position",
            f"- Current price: {margin.get('current_price')}",
            f"- Base midpoint: {margin.get('base_value_midpoint')}",
            f"- Position: {margin.get('position')}",
            "",
            "## Assumptions",
            f"- Forecast years: {reverse.get('forecast_years')}",
            f"- Discount rate: {pct(reverse.get('discount_rate'))}",
            f"- Terminal growth: {pct(reverse.get('terminal_growth'))}",
        ]
    )
    if result["warnings"]:
        lines.extend(["", "## Data Quality", *[f"- {warning}" for warning in result["warnings"]]])
    return "\n".join(lines).strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
