import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _event_classifier import classify_event  # noqa: E402
from _event_impact import event_impact_summary, thesis_impacts  # noqa: E402
from _event_materiality import event_materiality  # noqa: E402
from _event_parser import extract_events  # noqa: E402
from _event_report import render_event_markdown  # noqa: E402
from _event_timeline import build_event_intelligence  # noqa: E402
from v09_event_fixtures import (  # noqa: E402
    baseline,
    company,
    earnings_context,
    event_input,
    filing,
)


def test_8k_event_extraction_and_event_dates() -> None:
    events = extract_events(
        event_input(
            filing(
                "Item 2.02 Results of Operations. Revenue guidance was raised for FY2026.",
                accession="0002",
                filing_date="2026-08-20",
                item="Item 2.02",
            )
        )
    )

    assert events[0]["source_type"] == "SEC_8K"
    assert events[0]["published_at"] == "2026-08-20"
    assert events[0]["occurred_at"] == "2026-08-20"


def test_event_type_classification_uses_content_and_item() -> None:
    guidance = classify_event("Item 7.01", "Management raised revenue guidance.")
    acquisition = classify_event("Item 2.01", "The company completed an acquisition.")

    assert guidance == "GUIDANCE_CHANGE"
    assert acquisition == "ACQUISITION"


def test_event_deduplication_collapses_multiple_primary_sources() -> None:
    result = build_event_intelligence(
        event_input(
            filing("Guidance was raised for FY2026.", accession="0001"),
            filing("Guidance was raised for FY2026.", accession="0001"),
        )
    )

    assert len(result["events"]) == 1
    assert "EVENT_DUPLICATE_COLLAPSED" in result["warnings"]


def test_positive_negative_and_mixed_event_direction() -> None:
    result = build_event_intelligence(
        event_input(
            filing("Revenue guidance was raised.", accession="pos"),
            filing(
                "A new regulatory investigation and export restriction was announced.",
                accession="neg",
            ),
            filing("Debt was issued to fund capacity expansion.", accession="mixed"),
        )
    )
    directions = {event["event_id"]: event["direction"] for event in result["events"]}

    assert directions["NVDA-GUIDANCE_CHANGE-2026-08-20"] == "POSITIVE"
    assert directions["NVDA-REGULATORY-2026-08-20"] == "NEGATIVE"
    assert directions["NVDA-DEBT_ISSUANCE-2026-08-20"] == "MIXED"


def test_financial_materiality_low_and_high_events() -> None:
    low = event_materiality(
        {"event_type": "ACQUISITION", "amount": "2000000000"},
        company(),
    )
    high = event_materiality(
        {"event_type": "LITIGATION", "amount": "40000000000"},
        company(),
    )

    assert low == "LOW"
    assert high == "HIGH"


def test_announced_completed_and_cancelled_statuses() -> None:
    result = build_event_intelligence(
        event_input(
            filing("The acquisition was announced and remains pending.", accession="announced"),
            filing(
                "The acquisition was completed.", accession="completed", filing_date="2026-08-21"
            ),
            filing(
                "The partnership was cancelled.", accession="cancelled", filing_date="2026-08-22"
            ),
        )
    )
    statuses = {event["event_id"]: event["status"] for event in result["events"]}

    assert statuses["NVDA-ACQUISITION-2026-08-20"] == "ANNOUNCED"
    assert statuses["NVDA-ACQUISITION-2026-08-21"] == "COMPLETED"
    assert statuses["NVDA-PARTNERSHIP-2026-08-22"] == "CANCELLED"


def test_upcoming_official_catalyst_and_unconfirmed_rejection() -> None:
    result = build_event_intelligence(
        event_input(
            official_events=[
                {
                    "title": "Product availability",
                    "published_at": "2026-08-20",
                    "occurred_at": "2026-10-01",
                    "source_type": "OFFICIAL_NEWSROOM",
                    "source_url": "https://example.com/product",
                    "text": "Product availability begins on 2026-10-01.",
                    "confirmed": True,
                },
                {
                    "title": "Expected earnings date",
                    "published_at": "2026-08-20",
                    "text": "Expected earnings date based on cadence.",
                    "confirmed": False,
                },
            ]
        )
    )

    assert len(result["upcoming_catalysts"]) == 1
    assert "UPCOMING_CATALYST_DATE_UNCONFIRMED" in result["warnings"]


def test_event_thesis_dimension_mapping_and_impact_summary() -> None:
    result = build_event_intelligence(
        event_input(
            filing("Revenue guidance was raised.", accession="guide"),
            filing("A material lawsuit settlement was announced.", accession="risk"),
        )
    )

    impacts = thesis_impacts(result["events"])
    assert impacts["growth_outlook"][0]["direction"] == "POSITIVE"
    assert impacts["risk_level"][0]["direction"] == "NEGATIVE"
    assert event_impact_summary(result["events"]) == "MIXED_POSITIVE"


def test_earnings_and_guidance_events_reuse_earnings_context() -> None:
    result = build_event_intelligence(event_input(earnings_context=earnings_context("RAISED")))

    event = result["events"][0]
    assert event["event_type"] == "GUIDANCE_CHANGE"
    assert event["source_type"] == "EARNINGS_CONTEXT"
    assert event["evidence"][0]["source"] == "earnings_release"


def test_snapshot_relation_new_known_and_older() -> None:
    result = build_event_intelligence(
        event_input(
            filing("Revenue guidance was raised.", accession="new", filing_date="2026-08-20"),
            filing("A product launch was announced.", accession="known", filing_date="2026-08-15"),
            filing("A dividend was announced.", accession="old", filing_date="2026-08-01"),
            snapshot=baseline("2026-08-15T00:00:00Z"),
        )
    )
    relations = {event["event_id"]: event["snapshot_relation"] for event in result["events"]}

    assert relations["NVDA-GUIDANCE_CHANGE-2026-08-20"] == "NEW_SINCE_SNAPSHOT"
    assert relations["NVDA-PRODUCT_LAUNCH-2026-08-15"] == "ALREADY_KNOWN"
    assert relations["NVDA-DIVIDEND_CHANGE-2026-08-01"] == "OLDER_THAN_BASELINE"


def test_since_last_snapshot_filters_material_events() -> None:
    result = build_event_intelligence(
        event_input(
            filing("Revenue guidance was raised.", accession="new", filing_date="2026-08-20"),
            filing("A dividend was announced.", accession="old", filing_date="2026-08-01"),
            snapshot=baseline("2026-08-15T00:00:00Z"),
        ),
        since_last_snapshot=True,
    )

    assert [event["event_type"] for event in result["material_events"]] == ["GUIDANCE_CHANGE"]


def test_event_timeline_ordering_and_industry_shared_signal() -> None:
    result = build_event_intelligence(
        event_input(
            filing("A product launch was announced.", accession="late", filing_date="2026-08-22"),
            filing(
                "A regulatory export restriction was announced.",
                accession="early",
                filing_date="2026-08-20",
            ),
            peer_events={
                "AMD": [{"event_type": "REGULATORY", "direction": "NEGATIVE"}],
                "AVGO": [{"event_type": "REGULATORY", "direction": "NEGATIVE"}],
            },
        )
    )

    assert [event["published_at"] for event in result["material_events"]] == [
        "2026-08-20",
        "2026-08-22",
    ]
    assert result["industry_signals"][0]["signal"] == "industry_event_signal"


def test_no_primary_evidence_returns_warning() -> None:
    result = build_event_intelligence(event_input())

    assert result["events"] == []
    assert "EVENT_SOURCE_INCOMPLETE" in result["warnings"]
    assert "NO_MATERIAL_EVENTS" in result["warnings"]


def test_korean_and_english_event_reports_have_structure_without_forbidden_language() -> None:
    result = build_event_intelligence(event_input(filing("Revenue guidance was raised.")))

    korean = render_event_markdown(result, language="ko")
    english = render_event_markdown(result, language="en")
    combined = f"{korean}\n{english}"

    assert "핵심 이벤트" in korean
    assert "앞으로 확인할 촉매" in korean
    assert "Key Events" in english
    assert "Upcoming Catalysts" in english
    assert "SELL_TRIGGER" not in json.dumps(result)
    assert "stock rose because" not in combined.lower()
