from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Final

from _core import to_jsonable
from _thesis_tracker import build_thesis
from _valuation_intelligence import build_valuation_intelligence
from financial_health import financial_health
from risk import risk_checks
from valuation import valuation

VERSION: Final = "0.8.0"
SCHEMA_VERSION: Final = "research_snapshot.v1"
VOLATILE_KEYS: Final = {
    "created_at",
    "retrieved_at",
    "timestamp",
    "cache_timestamp",
    "market_quote",
    "path",
    "id",
}

FINANCIAL_FIELDS: Final = (
    "revenue",
    "revenue_growth",
    "net_income",
    "eps",
    "operating_margin",
    "net_margin",
    "operating_cash_flow",
    "free_cash_flow",
    "fcf_margin",
    "total_debt",
    "cash",
    "shares_outstanding",
)


def build_snapshot(
    company: dict[str, Any],
    *,
    research_context: dict[str, Any] | None = None,
    earnings_context: dict[str, Any] | None = None,
    valuation_context: dict[str, Any] | None = None,
    valuation_intelligence: dict[str, Any] | None = None,
    financial_quality: dict[str, Any] | None = None,
    risk_context: dict[str, Any] | None = None,
    peer_context: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    created = created_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    value = valuation_context or valuation(company)
    value = with_provided_metrics(value, company)
    earnings = earnings_context or nested_context(research_context, "earnings_context")
    intelligence = valuation_intelligence or build_valuation_intelligence(
        company, earnings_context=earnings
    )
    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "yourich_version": VERSION,
        "ticker": str(company.get("ticker") or ""),
        "company": str(company.get("company") or company.get("ticker") or ""),
        "created_at": created,
        "source_periods": source_periods(company),
        "market_price_date": market_price_date(company),
        "latest_filing_accession": latest_filing_accession(research_context),
        "latest_earnings_document": latest_earnings_document(earnings),
        "financials": financials(company, financial_quality),
        "financial_quality": financial_quality or financial_health(company),
        "valuation": value,
        "valuation_intelligence": intelligence,
        "risk": risk_context or risk_checks(company),
        "earnings": earnings or {},
        "research": research_context or {},
        "peer_context": peer_context or {},
        "data_quality": data_quality(company, value, intelligence, peer_context),
    }
    snapshot["thesis"] = build_thesis(snapshot)
    snapshot["fingerprint"] = snapshot_fingerprint(snapshot)
    return snapshot


def with_provided_metrics(value: dict[str, Any], company: dict[str, Any]) -> dict[str, Any]:
    provided = company.get("provided_metrics")
    if not isinstance(provided, dict):
        return value
    metrics = value.setdefault("metrics", {})
    if not isinstance(metrics, dict):
        return value
    for key, item in provided.items():
        existing = metrics.get(key)
        if isinstance(existing, dict):
            existing["value"] = item
    return value


def nested_context(context: dict[str, Any] | None, key: str) -> dict[str, Any] | None:
    if context is None:
        return None
    value = context.get(key)
    return value if isinstance(value, dict) else None


def financials(company: dict[str, Any], quality: dict[str, Any] | None) -> dict[str, Any]:
    metrics = quality.get("metrics", {}) if isinstance(quality, dict) else {}
    rows: dict[str, Any] = {}
    for field in FINANCIAL_FIELDS:
        rows[field] = {
            "value": metric_value(company, metrics, field),
            "basis": field_basis(company, field),
        }
    return rows


def metric_value(company: dict[str, Any], metrics: Any, field: str) -> Any:
    if company.get(field) is not None:
        return company.get(field)
    if field == "revenue_growth" and isinstance(metrics, dict):
        growth = metrics.get("revenue_growth")
        if isinstance(growth, dict):
            return growth.get("value")
    if field in {"operating_margin", "net_margin", "fcf_margin"} and isinstance(metrics, dict):
        margin = metrics.get(field)
        if isinstance(margin, dict):
            return margin.get("value")
    return company.get(field)


def field_basis(company: dict[str, Any], field: str) -> str | None:
    if field in {"revenue_growth", "operating_margin", "net_margin", "fcf_margin"}:
        return None
    metadata = company.get("fact_metadata", {}).get(field, {})
    if isinstance(metadata, dict) and metadata.get("basis") is not None:
        return str(metadata["basis"])
    return None


def source_periods(company: dict[str, Any]) -> dict[str, str | None]:
    return {field: field_basis(company, field) for field in FINANCIAL_FIELDS}


def market_price_date(company: dict[str, Any]) -> str | None:
    quote = company.get("market_quote")
    if isinstance(quote, dict) and quote.get("timestamp") is not None:
        return str(quote["timestamp"])
    return None


def latest_filing_accession(research_context: dict[str, Any] | None) -> str | None:
    if research_context is None:
        return None
    filing = research_context.get("latest_filing")
    if isinstance(filing, dict) and filing.get("accession") is not None:
        return str(filing["accession"])
    return None


def latest_earnings_document(earnings_context: dict[str, Any] | None) -> str | None:
    if earnings_context is None:
        return None
    latest = earnings_context.get("latest_earnings")
    if isinstance(latest, dict):
        return str(latest.get("accession") or latest.get("url") or latest.get("period") or "")
    return None


def data_quality(
    company: dict[str, Any],
    value: dict[str, Any],
    intelligence: dict[str, Any],
    peer_context: dict[str, Any] | None,
) -> dict[str, Any]:
    warnings = []
    warnings.extend(str(item) for item in company.get("warnings", []))
    warnings.extend(str(item) for item in value.get("warnings", []))
    warnings.extend(str(item) for item in intelligence.get("warnings", []))
    if peer_context is not None:
        warnings.extend(str(item) for item in peer_context.get("warnings", []))
    return {"warnings": sorted(set(warnings))}


def snapshot_identity(snapshot: dict[str, Any]) -> dict[str, str | None]:
    created = str(snapshot.get("created_at") or "")
    return {
        "id": safe_snapshot_id(created),
        "ticker": str(snapshot.get("ticker") or ""),
        "created_at": created,
        "schema_version": str(snapshot.get("schema_version") or ""),
        "yourich_version": str(snapshot.get("yourich_version") or ""),
    }


def safe_snapshot_id(created_at: str) -> str:
    return "".join(character for character in created_at if character.isalnum())


def snapshot_fingerprint(snapshot: dict[str, Any]) -> str:
    payload = stable_payload(snapshot)
    encoded = json.dumps(to_jsonable(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): stable_payload(item)
            for key, item in value.items()
            if str(key) not in VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [stable_payload(item) for item in value]
    return value
