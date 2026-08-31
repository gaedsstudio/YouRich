from __future__ import annotations

from datetime import date
from typing import Any

from _core import STALE_FINANCIAL_DAYS

SPLIT_WARNING_DAYS = 370


def provider_metadata(source: str, company: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    return {
        "fundamentals": {"name": "sec-companyfacts", "source": source},
        "market": company.get("market_quote"),
        "warnings": warnings,
    }


def freshness_warnings(company: dict[str, Any]) -> list[str]:
    freshness = company.get("data_freshness", {})
    if not isinstance(freshness, dict):
        return []
    filed = freshness.get("latest_financial_filed")
    market_day = freshness.get("market_price_date")
    if not isinstance(filed, str) or not isinstance(market_day, str):
        return []
    if (date.fromisoformat(market_day) - date.fromisoformat(filed)).days > STALE_FINANCIAL_DAYS:
        return ["STALE_FINANCIAL_DATA"]
    return []


def mapping_warnings(company: dict[str, Any]) -> list[str]:
    metadata = company.get("fact_metadata", {})
    if not isinstance(metadata, dict):
        return []
    warnings = []
    for field, item in metadata.items():
        if isinstance(item, dict) and item.get("confidence") == "LOW":
            warnings.append(f"LOW_CONFIDENCE_MAPPING:{field}")
        if isinstance(item, dict) and item.get("restated") is True:
            warnings.append(f"RESTATED_FACT:{field}")
    if potential_split_issue(metadata):
        warnings.append("POTENTIAL_SPLIT_ADJUSTMENT_ISSUE")
    return warnings


def currency_warnings(company: dict[str, Any]) -> list[str]:
    financial = company.get("financial_currency")
    market = company.get("market_currency")
    if isinstance(financial, str) and isinstance(market, str) and financial != market:
        return ["CURRENCY_MISMATCH"]
    return []


def data_quality(company: dict[str, Any]) -> dict[str, Any]:
    provider = company.get("provider")
    warnings = provider.get("warnings", []) if isinstance(provider, dict) else []
    return {
        "market_data": "delayed" if company.get("market_quote") else "missing",
        "fundamentals": "stale" if "STALE_FINANCIAL_DATA" in warnings else "current",
        "ttm_coverage": ttm_coverage(company),
        "mapping_confidence": mapping_confidence(company),
        "currency_match": "CURRENCY_MISMATCH" not in warnings,
        "restatement_risk": restatement_risk(warnings),
    }


def missing_fields(company: dict[str, Any]) -> list[str]:
    excluded = {
        "company",
        "ticker",
        "annuals",
        "provider",
        "missing_fields",
        "field_sources",
        "fact_metadata",
        "data_freshness",
        "data_quality",
        "market_quote",
        "selection_debug",
    }
    return [key for key, value in company.items() if key not in excluded and value is None]


def ttm_coverage(company: dict[str, Any]) -> str:
    metadata = company.get("fact_metadata", {})
    if not isinstance(metadata, dict):
        return "missing"
    required = ("revenue", "net_income", "eps", "operating_cash_flow", "capital_expenditures")
    bases = [
        metadata[field].get("basis") for field in required if isinstance(metadata.get(field), dict)
    ]
    if bases and all(str(basis).startswith("ttm") or basis == "diluted_ttm" for basis in bases):
        return "complete"
    return "partial"


def mapping_confidence(company: dict[str, Any]) -> str:
    metadata = company.get("fact_metadata", {})
    if not isinstance(metadata, dict):
        return "low"
    confidences = [item.get("confidence") for item in metadata.values() if isinstance(item, dict)]
    if "LOW" in confidences:
        return "low"
    if "MEDIUM" in confidences:
        return "medium"
    return "high"


def restatement_risk(warnings: list[Any]) -> str:
    if any(str(item).startswith("RESTATED_FACT") for item in warnings):
        return "detected"
    return "none"


def potential_split_issue(metadata: dict[Any, Any]) -> bool:
    eps = metadata.get("eps")
    shares = metadata.get("shares_outstanding")
    if not isinstance(eps, dict) or not isinstance(shares, dict):
        return False
    eps_end = eps.get("period_end")
    shares_end = shares.get("period_end")
    if not isinstance(eps_end, str) or not isinstance(shares_end, str):
        return False
    return (date.fromisoformat(shares_end) - date.fromisoformat(eps_end)).days > SPLIT_WARNING_DAYS
