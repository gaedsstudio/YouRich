import argparse

from _core import ToolError, write_json
from _filing_parser import clean_filing_html, extract_sections
from _filing_provider import SecFilingProvider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker")
    parser.add_argument("--form", action="append", dest="forms")
    parser.add_argument("--limit", default=5, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        provider = SecFilingProvider()
        filings = provider.get_filings(args.ticker, args.forms or ["10-K", "10-Q"], args.limit)
        payload = {"ticker": args.ticker.upper(), "filings": [item.to_dict() for item in filings]}
        if args.debug and filings:
            document = provider.get_document(filings[0])
            sections, warnings = extract_sections(clean_filing_html(document.html), filings[0].form)
            payload["latest_document"] = {
                "accession_number": filings[0].accession_number,
                "sections": [section.name for section in sections],
                "warnings": warnings,
            }
        write_json(payload)
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
