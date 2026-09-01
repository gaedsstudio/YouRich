from __future__ import annotations

import argparse
from typing import Any

from _core import ToolError, clean_ticker, read_payload, write_json
from _report_format import render_markdown
from _report_model import build_report
from _sec import fetch_financials


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", nargs="?")
    parser.add_argument("--ticker", dest="ticker_option")
    parser.add_argument("--input")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--language", choices=("en", "ko"), default="en")
    parser.add_argument("--research-context")
    args = parser.parse_args()
    try:
        company = load_company(args)
        research_context = read_payload(args.research_context) if args.research_context else None
        report = build_report(company, research_context=research_context, language=args.language)
        if args.format == "json":
            write_json(report.to_dict())
        else:
            print(render_markdown(report), end="")
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


def load_company(args: argparse.Namespace) -> dict[str, Any]:
    ticker = args.ticker_option or args.ticker
    if args.input and ticker:
        raise ToolError("use either --input or ticker, not both")
    if args.input:
        return read_payload(args.input)
    if ticker:
        return fetch_financials(clean_ticker(ticker))
    raise ToolError("ticker or --input is required")


if __name__ == "__main__":
    raise SystemExit(main())
