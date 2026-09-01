from __future__ import annotations

import argparse
from typing import Any

from _core import ToolError, clean_ticker, read_payload, write_json
from _research_diff import compare_snapshots
from _research_snapshot import build_snapshot
from _research_store import ResearchStore
from _sec import fetch_financials
from _tracking_report import render_tracking_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("command", choices=("capture", "compare", "history", "latest"))
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--language", choices=("en", "ko"), default="en")
    parser.add_argument("--store-dir")
    parser.add_argument("--input")
    parser.add_argument("--against")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--created-at")
    args = parser.parse_args()
    try:
        result = run(args)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    if args.format == "markdown":
        print(markdown_for(args.command, result, args.language), end="")
    else:
        write_json(result)
    return 0


def run(args: argparse.Namespace) -> dict[str, Any]:
    ticker = clean_ticker(args.ticker)
    store = ResearchStore(args.store_dir)
    if args.command == "history":
        return {"ticker": ticker, "snapshots": store.history(ticker)[-args.limit :]}
    if args.command == "latest":
        return {"ticker": ticker, "snapshot": store.latest(ticker)}
    snapshot = build_snapshot(load_company(ticker, args.input), created_at=args.created_at)
    if args.command == "capture":
        return store.capture(snapshot)
    if args.against:
        previous = store.by_id(ticker, args.against)
        if previous is None:
            raise ToolError(f"snapshot not found: {args.against}")
        current_ref = store.save(snapshot)
        current = dict(snapshot)
        current.update(current_ref)
        return compare_snapshots(previous, current)
    return store.compare_or_capture_baseline(snapshot)


def load_company(ticker: str, input_path: str | None) -> dict[str, Any]:
    if input_path:
        payload = read_payload(input_path)
        payload["ticker"] = str(payload.get("ticker") or ticker)
        return payload
    return fetch_financials(ticker)


def markdown_for(command: str, result: dict[str, Any], language: str) -> str:
    if command in {"capture", "compare"}:
        return render_tracking_markdown(result, language)
    if command == "latest":
        snapshot = result.get("snapshot")
        return f"# {result.get('ticker')} Latest Snapshot\n\n{snapshot_date(snapshot)}\n"
    lines = [f"# {result.get('ticker')} Research History", ""]
    for item in result.get("snapshots", []):
        if isinstance(item, dict):
            thesis = item.get("thesis", {})
            overall = thesis.get("overall_thesis") if isinstance(thesis, dict) else None
            lines.extend([str(item.get("created_at")), str(overall or "INSUFFICIENT_DATA"), ""])
    return "\n".join(lines).strip() + "\n"


def snapshot_date(value: Any) -> str:
    if isinstance(value, dict) and value.get("created_at") is not None:
        return str(value["created_at"])
    return "Unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
