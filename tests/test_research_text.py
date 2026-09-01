import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _filing_types import FilingSection  # noqa: E402
from _research_text import section_excerpt  # noqa: E402


def test_section_excerpt_starts_at_sentence_boundary() -> None:
    section = FilingSection(
        name="business",
        item="Item 1. Business",
        text=(
            "Forward-looking boilerplate should be skipped before the useful sentence. "
            "AMD is positioned across cloud, edge, embedded, and end devices with AI "
            "platform demand supporting growth."
        ),
    )

    excerpt = section_excerpt(section, ("platform",))

    assert excerpt.startswith("AMD is positioned")
