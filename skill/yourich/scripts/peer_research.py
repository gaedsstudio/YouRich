from __future__ import annotations

import argparse
from typing import Any

from _core import ToolError, clean_ticker, read_payload, write_json
from _peer_analysis import build_peer_research
from _peer_discovery import automatic_peer_tickers
from _peer_report import render_peer_markdown
from _sec import fetch_financials


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", nargs="?")
    parser.add_argument("--peers", nargs="*")
    parser.add_argument("--input")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--language", choices=("en", "ko"), default="en")
    args = parser.parse_args()
    try:
        result = build_from_args(args)
        if args.format == "markdown":
            print(render_peer_markdown(result, args.language), end="")
        else:
            write_json(result)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


def build_from_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        payload = read_payload(args.input)
        company = payload.get("company")
        peers = payload.get("peers", [])
        if not isinstance(company, dict) or not isinstance(peers, list):
            raise ToolError("input must contain object company and list peers")
        return build_peer_research(company, [peer for peer in peers if isinstance(peer, dict)])
    if not args.ticker:
        raise ToolError("ticker or --input is required")
    company = fetch_financials(clean_ticker(args.ticker))
    tickers = args.peers if args.peers else automatic_peer_tickers(args.ticker)
    peers = [fetch_financials(clean_ticker(peer)) for peer in tickers]
    return build_peer_research(company, peers)


if __name__ == "__main__":
    raise SystemExit(main())
