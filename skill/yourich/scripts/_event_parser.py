from __future__ import annotations

from typing import Any

from _event_classifier import classify_event


def extract_events(source_context: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    events.extend(events_from_filings(source_context))
    events.extend(events_from_official_events(source_context))
    events.extend(events_from_earnings(source_context))
    return events


def events_from_filings(source_context: dict[str, Any]) -> list[dict[str, Any]]:
    ticker = str(
        source_context.get("ticker") or source_context.get("company", {}).get("ticker") or ""
    )
    events = []
    for filing in source_context.get("filings", []):
        if not isinstance(filing, dict) or filing.get("form") != "8-K":
            continue
        text = str(filing.get("text") or filing.get("html") or "")
        item = str(filing.get("item") or " ".join(str(value) for value in filing.get("items", [])))
        event_type = classify_event(item, text)
        date = str(filing.get("filing_date") or filing.get("published_at") or "")
        events.append(
            base_event(
                ticker=ticker,
                event_type=event_type,
                title=title_for(event_type, text),
                text=text,
                published_at=date,
                occurred_at=str(filing.get("occurred_at") or date),
                source_type="SEC_8K",
                source_url=str(filing.get("filing_url") or filing.get("source_url") or ""),
                evidence=[
                    {"source": "sec_filing", "accession": str(filing.get("accession") or "")}
                ],
            )
        )
    return events


def events_from_official_events(source_context: dict[str, Any]) -> list[dict[str, Any]]:
    ticker = str(
        source_context.get("ticker") or source_context.get("company", {}).get("ticker") or ""
    )
    events = []
    for item in source_context.get("official_events", []):
        if not isinstance(item, dict) or item.get("confirmed") is False:
            continue
        text = str(item.get("text") or item.get("title") or "")
        event_type = classify_event(str(item.get("item") or ""), text)
        date = str(item.get("published_at") or item.get("occurred_at") or "")
        events.append(
            base_event(
                ticker=ticker,
                event_type=event_type,
                title=str(item.get("title") or title_for(event_type, text)),
                text=text,
                published_at=date,
                occurred_at=str(item.get("occurred_at") or date),
                source_type=str(item.get("source_type") or "OFFICIAL_IR"),
                source_url=str(item.get("source_url") or ""),
                evidence=[{"source": str(item.get("source_type") or "official_source")}],
            )
        )
    return events


def events_from_earnings(source_context: dict[str, Any]) -> list[dict[str, Any]]:
    context = source_context.get("earnings_context")
    if not isinstance(context, dict):
        return []
    ticker = str(
        source_context.get("ticker") or source_context.get("company", {}).get("ticker") or ""
    )
    changes = context.get("guidance_changes")
    if isinstance(changes, list) and changes:
        latest = context.get("latest_earnings", {})
        published = latest.get("reported_at") if isinstance(latest, dict) else None
        return [
            base_event(
                ticker=ticker,
                event_type="GUIDANCE_CHANGE",
                title="Guidance change",
                text=" ".join(
                    str(change.get("status") or "")
                    for change in changes
                    if isinstance(change, dict)
                ),
                published_at=str(published or ""),
                occurred_at=str(published or ""),
                source_type="EARNINGS_CONTEXT",
                source_url="",
                evidence=list(context.get("evidence", []))
                if isinstance(context.get("evidence"), list)
                else [],
            )
        ]
    return []


def base_event(**kwargs: Any) -> dict[str, Any]:
    event = dict(kwargs)
    event["event_id"] = f"{event['ticker']}-{event['event_type']}-{event['published_at']}"
    return event


def title_for(event_type: str, text: str) -> str:
    if text.strip():
        return text.strip().split(".")[0][:120]
    return event_type.replace("_", " ").title()
