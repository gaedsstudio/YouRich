from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from _core import ToolError, read_payload, write_json
from _earnings import build_earnings_context, parse_earnings_request
from _earnings_report import render_earnings_markdown
from _earnings_types import EarningsDocument


@dataclass(frozen=True, slots=True)
class FixtureEarningsProvider:
    documents: list[EarningsDocument]
    text_dir: Path

    def get_documents(self, _ticker: str, history: int) -> list[EarningsDocument]:
        return self.documents[:history]

    def get_document_text(self, document: EarningsDocument) -> str:
        name = "current.txt" if document.source_url.endswith("/current") else "previous.txt"
        return (self.text_dir / name).read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--history", default=2, type=int)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--language", choices=("en", "ko"), default="en")
    parser.add_argument("--financials")
    parser.add_argument("--fixture-documents")
    parser.add_argument("--fixture-text-dir")
    args = parser.parse_args()
    try:
        financials = read_payload(args.financials) if args.financials else None
        provider = fixture_provider(args.fixture_documents, args.fixture_text_dir)
        request = parse_earnings_request(args.ticker, args.history, financials)
        context = build_earnings_context(request, provider)
        if args.format == "markdown":
            print(render_earnings_markdown(context, args.language), end="")
        else:
            write_json(context)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


def fixture_provider(
    documents_path: str | None, text_dir: str | None
) -> FixtureEarningsProvider | None:
    if documents_path is None:
        return None
    if text_dir is None:
        raise ToolError("--fixture-text-dir is required with --fixture-documents")
    payload = json.loads(Path(documents_path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ToolError("fixture documents must be a JSON list")
    documents = [
        EarningsDocument(
            ticker=str(item["ticker"]),
            company=str(item["company"]),
            document_type=str(item["document_type"]),
            published_at=str(item["published_at"]),
            period_end=str(item["period_end"]) if item.get("period_end") is not None else None,
            source_url=str(item["source_url"]),
            source_type=str(item["source_type"]),
            title=str(item["title"]),
            retrieved_at=str(item["retrieved_at"]),
        )
        for item in payload
        if isinstance(item, dict)
    ]
    return FixtureEarningsProvider(documents, Path(text_dir))


if __name__ == "__main__":
    raise SystemExit(main())
