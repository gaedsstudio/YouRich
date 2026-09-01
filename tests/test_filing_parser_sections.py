import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _filing_parser import extract_sections  # noqa: E402


def test_extract_sections_skips_table_of_contents_markers() -> None:
    text = (
        "Table of Contents Item 1. Business 1 Item 1A. Risk Factors 14 "
        "Item 7. Management's Discussion and Analysis 42\n\n"
        "Item 1. Business Revenue comes from data center and client products.\n"
        "Item 1A. Risk Factors Competition and supply constraints could affect results.\n"
        "Item 7. Management's Discussion and Analysis Revenue and margins changed."
    )

    sections, warnings = extract_sections(text, "10-K")

    assert warnings == []
    assert sections[0].name == "business"
    assert "Table of Contents" not in sections[0].text
    assert "Revenue comes from data center and client products." in sections[0].text
