from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from _core import decimal_or_none


def event_materiality(event: dict[str, Any], company: dict[str, Any]) -> str:
    amount = decimal_or_none(event.get("amount")) or amount_from_text(str(event.get("text") or ""))
    if amount is None:
        return default_materiality(str(event.get("event_type") or ""))
    base = materiality_base(str(event.get("event_type") or ""), company)
    if base is None or base <= 0:
        return "MEDIUM"
    ratio = abs(amount) / base
    if ratio >= Decimal("1"):
        return "CRITICAL"
    if ratio >= Decimal("0.50"):
        return "HIGH"
    if ratio >= Decimal("0.01"):
        return "MEDIUM"
    return "LOW"


def amount_from_text(text: str) -> Decimal | None:
    match = re.search(
        r"(\$)?\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|bn|m)?",
        text,
        re.IGNORECASE,
    )
    if match is None:
        return None
    dollar = match.group(1)
    unit = match.group(3)
    if dollar is None and unit is None:
        return None
    try:
        value = Decimal(match.group(2))
    except InvalidOperation:
        return None
    unit = (unit or "").lower()
    if unit in {"billion", "bn"}:
        return value * Decimal("1000000000")
    if unit in {"million", "m"}:
        return value * Decimal("1000000")
    return value


def materiality_base(event_type: str, company: dict[str, Any]) -> Decimal | None:
    if event_type in {"LITIGATION", "RESTATEMENT"}:
        return decimal_or_none(company.get("net_income"))
    if event_type in {"CAPEX_CHANGE", "CAPACITY_EXPANSION"}:
        return decimal_or_none(company.get("capital_expenditures")) or decimal_or_none(
            company.get("revenue")
        )
    if event_type in {"DEBT_ISSUANCE", "DEBT_REPAYMENT"}:
        return decimal_or_none(company.get("total_assets"))
    return decimal_or_none(company.get("market_cap")) or decimal_or_none(company.get("revenue"))


def default_materiality(event_type: str) -> str:
    if event_type in {"REGULATORY", "RESTATEMENT", "SECURITY_INCIDENT"}:
        return "HIGH"
    if event_type in {"GUIDANCE_CHANGE", "EARNINGS_RESULT", "ACQUISITION", "PRODUCT_LAUNCH"}:
        return "MEDIUM"
    return "MEDIUM"
