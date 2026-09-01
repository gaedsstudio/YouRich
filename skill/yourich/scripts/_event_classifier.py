from __future__ import annotations

from collections.abc import Iterable

CLASSIFICATION_RULES = (
    ("GUIDANCE_CHANGE", ("guidance", "outlook", "forecast")),
    ("EARNINGS_RESULT", ("earnings", "results of operations", "quarterly results")),
    ("SHARE_REPURCHASE", ("share repurchase", "buyback")),
    ("DIVIDEND_CHANGE", ("dividend",)),
    ("DEBT_ISSUANCE", ("debt was issued", "issued debt", "notes offering", "senior notes")),
    ("DEBT_REPAYMENT", ("repaid debt", "debt repayment", "redeemed notes")),
    ("ACQUISITION", ("acquisition", "item 2.01")),
    ("DIVESTITURE", ("divestiture", "sale of business")),
    ("PARTNERSHIP", ("partnership", "collaboration")),
    ("CUSTOMER_WIN", ("customer win", "new customer", "awarded contract")),
    ("CUSTOMER_LOSS", ("customer loss", "lost customer")),
    ("SUPPLY_CHANGE", ("supply", "supplier", "shortage")),
    ("CAPACITY_EXPANSION", ("capacity expansion", "new facility", "expanded capacity")),
    ("CAPEX_CHANGE", ("capex", "capital expenditure")),
    ("CEO_CHANGE", ("ceo",)),
    ("CFO_CHANGE", ("cfo",)),
    ("MANAGEMENT_CHANGE", ("management change", "appointed", "resigned")),
    ("RESTRUCTURING", ("restructuring", "reorganization")),
    ("LAYOFF", ("layoff", "workforce reduction")),
    ("REGULATORY", ("regulatory", "investigation", "export restriction", "sanction")),
    ("LITIGATION", ("litigation", "lawsuit", "settlement", "legal proceeding")),
    ("PRODUCT_LAUNCH", ("product launch", "availability begins", "launched")),
    ("PRODUCT_DELAY", ("product delay", "delayed launch", "postponed")),
    ("SECURITY_INCIDENT", ("security incident", "breach", "cybersecurity")),
    ("ACCOUNTING_CHANGE", ("accounting change", "accounting policy")),
    ("RESTATEMENT", ("restatement", "restate")),
    ("SEGMENT_CHANGE", ("segment", "reportable segment")),
    ("CAPITAL_ALLOCATION", ("capital allocation", "cash return")),
)


def classify_event(item: str, text: str) -> str:
    value = f"{item} {text}".lower()
    for event_type, needles in CLASSIFICATION_RULES:
        if has(value, needles):
            return event_type
    return "OTHER_MATERIAL_EVENT"


def event_direction(event_type: str, text: str) -> str:
    value = text.lower()
    if event_type == "DEBT_ISSUANCE" and has(value, ("fund", "capacity", "expansion")):
        return "MIXED"
    if event_type in {"REGULATORY", "LITIGATION", "SECURITY_INCIDENT", "RESTATEMENT"}:
        return "NEGATIVE"
    if has(value, ("raised", "increase", "win", "settlement", "completed", "launched")):
        return "POSITIVE"
    if has(value, ("lowered", "decline", "loss", "cancelled", "restriction", "investigation")):
        return "NEGATIVE"
    if event_type in {"PRODUCT_DELAY", "CUSTOMER_LOSS", "LAYOFF"}:
        return "NEGATIVE"
    return "NEUTRAL"


def event_status(text: str) -> str:
    value = text.lower()
    if "cancelled" in value or "canceled" in value:
        return "CANCELLED"
    if "completed" in value or "closed" in value:
        return "COMPLETED"
    if "pending" in value:
        return "ANNOUNCED"
    if "announced" in value:
        return "ANNOUNCED"
    return "REALIZED"


def catalyst_class(direction: str, event_type: str) -> str:
    if direction == "POSITIVE":
        return "POSITIVE_CATALYST"
    if direction == "NEGATIVE" and event_type in {"REGULATORY", "LITIGATION", "SECURITY_INCIDENT"}:
        return "RISK_EVENT"
    if direction == "NEGATIVE":
        return "NEGATIVE_CATALYST"
    if event_type in {"ACQUISITION", "DIVESTITURE", "SEGMENT_CHANGE", "MANAGEMENT_CHANGE"}:
        return "STRUCTURAL_CHANGE"
    return "INFORMATIONAL"


def thesis_dimensions(event_type: str) -> list[str]:
    mapping = {
        "GUIDANCE_CHANGE": ["growth_outlook", "valuation_attractiveness"],
        "EARNINGS_RESULT": ["financial_quality", "growth_outlook"],
        "SHARE_REPURCHASE": ["financial_quality", "valuation_attractiveness"],
        "DIVIDEND_CHANGE": ["financial_quality"],
        "DEBT_ISSUANCE": ["financial_quality", "growth_outlook"],
        "ACQUISITION": ["business_quality", "growth_outlook"],
        "PARTNERSHIP": ["business_quality", "growth_outlook"],
        "CUSTOMER_WIN": ["business_quality", "growth_outlook"],
        "CUSTOMER_LOSS": ["business_quality", "growth_outlook", "risk_level"],
        "CAPACITY_EXPANSION": ["growth_outlook", "financial_quality"],
        "MANAGEMENT_CHANGE": ["business_quality", "risk_level"],
        "REGULATORY": ["risk_level", "growth_outlook"],
        "LITIGATION": ["risk_level", "financial_quality"],
        "PRODUCT_LAUNCH": ["growth_outlook", "business_quality"],
        "PRODUCT_DELAY": ["growth_outlook", "risk_level"],
        "RESTATEMENT": ["financial_quality", "risk_level"],
    }
    return mapping.get(event_type, ["business_quality"])


def has(value: str, needles: Iterable[str]) -> bool:
    return any(needle in value for needle in needles)
