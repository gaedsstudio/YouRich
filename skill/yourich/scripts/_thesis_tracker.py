from __future__ import annotations

from decimal import Decimal
from typing import Any, Final

from _core import decimal_or_none

STRONG_MARGIN: Final = Decimal("20")
STRONG_GROWTH: Final = Decimal("15")
HIGH_PE: Final = Decimal("40")
HIGH_REQUIRED_GROWTH: Final = Decimal("20")
FCF_MARGIN_TRIGGER: Final = Decimal("35")


def build_thesis(snapshot: dict[str, Any]) -> dict[str, Any]:
    financials = snapshot.get("financials", {})
    valuation = snapshot.get("valuation", {})
    intelligence = snapshot.get("valuation_intelligence", {})
    risks = snapshot.get("risk", {})
    thesis = {
        "business_quality": business_quality(snapshot),
        "financial_quality": financial_quality(financials),
        "growth_outlook": growth_outlook(financials),
        "valuation_attractiveness": valuation_attractiveness(valuation, intelligence),
        "risk_level": risk_level(risks),
    }
    thesis["overall_thesis"] = overall_thesis(thesis)
    thesis["watch_variables"] = watch_variables(snapshot)
    thesis["thesis_risk_conditions"] = thesis_risk_conditions(snapshot)
    return thesis


def business_quality(snapshot: dict[str, Any]) -> str:
    research = snapshot.get("research", {})
    if isinstance(research, dict) and research:
        confidence = str(research.get("research_confidence") or "")
        if confidence == "HIGH":
            return "STRONG"
    return "INSUFFICIENT_EVIDENCE"


def financial_quality(financials: Any) -> str:
    net_margin = financial_metric(financials, "net_margin")
    fcf_margin = financial_metric(financials, "fcf_margin")
    if net_margin is None and fcf_margin is None:
        return "INSUFFICIENT_EVIDENCE"
    if (net_margin or Decimal("0")) >= STRONG_MARGIN and (fcf_margin or Decimal("0")) >= Decimal(
        "10"
    ):
        return "STRONG"
    return "WEAK"


def growth_outlook(financials: Any) -> str:
    growth = financial_metric(financials, "revenue_growth")
    if growth is None:
        return "INSUFFICIENT_EVIDENCE"
    if growth >= STRONG_GROWTH:
        return "STRONG"
    if growth >= Decimal("0"):
        return "MODERATE"
    return "WEAK"


def valuation_attractiveness(valuation: Any, intelligence: Any) -> str:
    pe = valuation_metric(valuation, "pe")
    required = reverse_dcf_metric(intelligence, "required_fcf_cagr")
    if pe is None and required is None:
        return "INSUFFICIENT_EVIDENCE"
    if (pe is not None and pe >= HIGH_PE) or (
        required is not None and required >= HIGH_REQUIRED_GROWTH
    ):
        return "WEAK"
    return "MODERATE"


def risk_level(risks: Any) -> str:
    checks = risks.get("risk_checks", []) if isinstance(risks, dict) else []
    triggered = [
        item for item in checks if isinstance(item, dict) and str(item.get("status")) == "triggered"
    ]
    if not triggered:
        return "LOW"
    if any(str(item.get("severity")) == "high" for item in triggered):
        return "HIGH"
    return "MODERATE"


def overall_thesis(thesis: dict[str, Any]) -> str:
    quality = thesis.get("financial_quality")
    valuation = thesis.get("valuation_attractiveness")
    if quality == "STRONG" and valuation == "WEAK":
        return "HIGH QUALITY / EXPENSIVE"
    if quality == "STRONG":
        return "HIGH QUALITY"
    if quality == "WEAK" and valuation == "MODERATE":
        return "LOW QUALITY / CHEAP"
    return "INSUFFICIENT DATA"


def watch_variables(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    financials = snapshot.get("financials", {})
    intelligence = snapshot.get("valuation_intelligence", {})
    rows = []
    fcf_margin = financial_metric(financials, "fcf_margin")
    if fcf_margin is not None:
        rows.append(
            {
                "name": "FCF margin",
                "current": f"{fcf_margin}%",
                "watch_reason": "Supports current valuation quality.",
                "negative_trigger": f"< {FCF_MARGIN_TRIGGER:.1f}%",
            }
        )
    revenue_growth = financial_metric(financials, "revenue_growth")
    if revenue_growth is not None:
        rows.append(
            {
                "name": "Revenue growth",
                "current": f"{revenue_growth}%",
                "watch_reason": "Shows whether growth outlook is strengthening or fading.",
                "negative_trigger": "< 0.0%",
            }
        )
    required = reverse_dcf_metric(intelligence, "required_fcf_cagr")
    if required is not None:
        rows.append(
            {
                "name": "Required FCF CAGR",
                "current": f"{required}%",
                "watch_reason": "Measures how demanding the current valuation is.",
                "negative_trigger": f"> {HIGH_REQUIRED_GROWTH}%",
            }
        )
    return rows


def thesis_risk_conditions(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for variable in watch_variables(snapshot):
        trigger = variable.get("negative_trigger")
        if trigger:
            rows.append(
                {
                    "type": "THESIS_RISK_CONDITION",
                    "condition": f"{variable['name']} {trigger}",
                    "evidence": variable["current"],
                }
            )
    return rows


def financial_metric(financials: Any, key: str) -> Decimal | None:
    if not isinstance(financials, dict):
        return None
    row = financials.get(key)
    if isinstance(row, dict):
        return decimal_or_none(row.get("value"))
    return None


def valuation_metric(valuation: Any, key: str) -> Decimal | None:
    if not isinstance(valuation, dict):
        return None
    metrics = valuation.get("metrics")
    if not isinstance(metrics, dict):
        return None
    row = metrics.get(key)
    if isinstance(row, dict):
        return decimal_or_none(row.get("value"))
    return None


def reverse_dcf_metric(intelligence: Any, key: str) -> Decimal | None:
    if not isinstance(intelligence, dict):
        return None
    reverse = intelligence.get("reverse_dcf")
    if isinstance(reverse, dict):
        return decimal_or_none(reverse.get(key))
    return None
