from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from _event_classifier import catalyst_class, event_direction, event_status, thesis_dimensions
from _event_impact import event_impact_summary, thesis_impacts
from _event_materiality import event_materiality
from _event_parser import extract_events
from _event_types import VERSION

MIN_INDUSTRY_SIGNAL_PEERS = 2


def build_event_intelligence(
    source_context: dict[str, Any], since_last_snapshot: bool = False, days: int = 90
) -> dict[str, Any]:
    warnings = initial_warnings(source_context)
    company = company_payload(source_context)
    events = dedupe(
        [enrich_event(event, company, source_context) for event in extract_events(source_context)],
        warnings,
    )
    material = [event for event in events if event.get("materiality") != "LOW"]
    if since_last_snapshot:
        material = [
            event for event in material if event.get("snapshot_relation") == "NEW_SINCE_SNAPSHOT"
        ]
    material = sorted(material, key=event_sort_key)
    if not material:
        warnings.append("NO_MATERIAL_EVENTS")
    return {
        "version": VERSION,
        "ticker": str(company.get("ticker") or source_context.get("ticker") or ""),
        "company": str(company.get("company") or company.get("company_name") or ""),
        "window": {"days": days, "since_last_snapshot": since_last_snapshot},
        "events": sorted(events, key=event_sort_key),
        "material_events": material,
        "upcoming_catalysts": upcoming_catalysts(events),
        "thesis_impacts": thesis_impacts(material),
        "event_impact_summary": event_impact_summary(material),
        "snapshot_relation": snapshot_summary(events),
        "industry_signals": industry_signals(source_context.get("peer_events")),
        "warnings": sorted(set(warnings)),
        "data_quality": data_quality(events, warnings),
    }


def enrich_event(
    event: dict[str, Any], company: dict[str, Any], source_context: dict[str, Any]
) -> dict[str, Any]:
    enriched = dict(event)
    text = str(enriched.get("text") or enriched.get("title") or "")
    event_type = str(enriched.get("event_type") or "OTHER_MATERIAL_EVENT")
    enriched["direction"] = event_direction(event_type, text)
    enriched["materiality"] = event_materiality(enriched, company)
    enriched["status"] = event_status(text)
    enriched["thesis_dimensions"] = thesis_dimensions(event_type)
    enriched["catalyst_class"] = catalyst_class(enriched["direction"], event_type)
    enriched["snapshot_relation"] = snapshot_relation(enriched, source_context.get("snapshot"))
    enriched["supporting_sources"] = [source_ref(enriched)]
    return enriched


def dedupe(events: list[dict[str, Any]], warnings: list[str]) -> list[dict[str, Any]]:
    collapsed: dict[str, dict[str, Any]] = {}
    for event in events:
        key = str(event.get("event_id") or stable_key(event))
        if key not in collapsed:
            collapsed[key] = event
            continue
        warnings.append("EVENT_DUPLICATE_COLLAPSED")
        collapsed[key]["supporting_sources"].extend(event.get("supporting_sources", []))
        collapsed[key]["evidence"].extend(event.get("evidence", []))
    return list(collapsed.values())


def upcoming_catalysts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = datetime.now(UTC).date()
    catalysts = []
    for event in events:
        occurred = parse_date(str(event.get("occurred_at") or ""))
        if occurred is None or occurred <= today:
            continue
        item = dict(event)
        item["catalyst_status"] = "UPCOMING"
        catalysts.append(item)
    return sorted(catalysts, key=event_sort_key)


def snapshot_relation(event: dict[str, Any], snapshot: Any) -> str:
    if not isinstance(snapshot, dict):
        return "EVENT_SNAPSHOT_RELATION_UNKNOWN"
    baseline = parse_date(str(snapshot.get("created_at") or ""))
    event_date = parse_date(str(event.get("published_at") or event.get("occurred_at") or ""))
    if baseline is None or event_date is None:
        return "EVENT_SNAPSHOT_RELATION_UNKNOWN"
    if event_date > baseline:
        return "NEW_SINCE_SNAPSHOT"
    if event_date == baseline:
        return "ALREADY_KNOWN"
    return "OLDER_THAN_BASELINE"


def initial_warnings(source_context: dict[str, Any]) -> list[str]:
    warnings = [
        "UPCOMING_CATALYST_DATE_UNCONFIRMED"
        for item in source_context.get("official_events", [])
        if isinstance(item, dict) and item.get("confirmed") is False
    ]
    if not any(
        source_context.get(key) for key in ("filings", "official_events", "earnings_context")
    ):
        warnings.append("EVENT_SOURCE_INCOMPLETE")
    return warnings


def industry_signals(peer_events: Any) -> list[dict[str, Any]]:
    if not isinstance(peer_events, dict):
        return []
    counts: dict[tuple[str, str], list[str]] = {}
    for ticker, events in peer_events.items():
        if not isinstance(events, list):
            continue
        for event in events:
            if isinstance(event, dict):
                key = (str(event.get("event_type")), str(event.get("direction")))
                counts.setdefault(key, []).append(str(ticker))
    return [
        {
            "signal": "industry_event_signal",
            "event_type": key[0],
            "direction": key[1],
            "peers": peers,
        }
        for key, peers in counts.items()
        if len(set(peers)) >= MIN_INDUSTRY_SIGNAL_PEERS
    ]


def snapshot_summary(events: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"NEW_SINCE_SNAPSHOT": 0, "ALREADY_KNOWN": 0, "OLDER_THAN_BASELINE": 0}
    for event in events:
        relation = str(event.get("snapshot_relation") or "")
        if relation in summary:
            summary[relation] += 1
    return summary


def data_quality(events: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    return {
        "event_count": len(events),
        "primary_source_only": True,
        "warnings": sorted(set(warnings)),
    }


def company_payload(source_context: dict[str, Any]) -> dict[str, Any]:
    company = source_context.get("company")
    return company if isinstance(company, dict) else {}


def parse_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def event_sort_key(event: dict[str, Any]) -> str:
    return str(event.get("published_at") or event.get("occurred_at") or "")


def source_ref(event: dict[str, Any]) -> dict[str, str]:
    return {
        "source_type": str(event.get("source_type") or ""),
        "source_url": str(event.get("source_url") or ""),
    }


def stable_key(event: dict[str, Any]) -> str:
    return f"{event.get('ticker')}-{event.get('event_type')}-{event.get('published_at')}"
