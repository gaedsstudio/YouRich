import argparse
import sys
from pathlib import Path

from _core import write_json
from _filing_parser import clean_filing_html, extract_sections


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="-")
    parser.add_argument("--form", default="10-K")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    sections, warnings = extract_sections(clean_filing_html(raw), args.form)
    write_json({"sections": [section.to_dict() for section in sections], "warnings": warnings})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
