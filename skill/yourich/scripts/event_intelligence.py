from __future__ import annotations

import argparse
from typing import Any

from _core import ToolError, clean_ticker, read_payload, write_json
from _event_report import render_event_markdown
from _event_sources import build_source_context
from _event_timeline import build_event_intelligence
from _research_store import ResearchStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--input")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--language", choices=("en", "ko"), default="en")
    parser.add_argument("--since-last-snapshot", action="store_true")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--store-dir")
    args = parser.parse_args()
    try:
        result = run(args)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    if args.format == "markdown":
        print(render_event_markdown(result, args.language), end="")
    else:
        write_json(result)
    return 0


def run(args: argparse.Namespace) -> dict[str, Any]:
    ticker = clean_ticker(args.ticker)
    context = read_payload(args.input) if args.input else build_source_context(ticker, args.days)
    context["ticker"] = str(context.get("ticker") or ticker)
    context.setdefault("company", {"ticker": ticker})
    if args.since_last_snapshot and "snapshot" not in context:
        snapshot = ResearchStore(args.store_dir).latest(ticker)
        if snapshot is not None:
            context["snapshot"] = snapshot
    return build_event_intelligence(context, args.since_last_snapshot, args.days)


if __name__ == "__main__":
    raise SystemExit(main())
