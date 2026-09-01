from __future__ import annotations

from typing import Any


def overall_label(rows: list[dict[str, str]]) -> str:
    values = {row["Area"]: row["Assessment"] for row in rows}
    quality = values.get("Profitability")
    valuation_label = values.get("Valuation", "").upper()
    if quality in {"Very Strong", "Strong"} and "EXPENSIVE" in valuation_label:
        return "HIGH QUALITY / EXPENSIVE"
    if quality in {"Very Strong", "Strong"}:
        return "HIGH QUALITY / " + values.get("Valuation", "FAIRLY VALUED").upper()
    if values.get("Evidence Quality") == "Low":
        return "INSUFFICIENT DATA"
    return values.get("Valuation", "FAIRLY VALUED").upper()


def overall_summary(label: str, language: str) -> str:
    if language == "ko":
        if "EXPENSIVE" in label:
            return "수익성과 현금창출력은 강하지만, 현재 평가는 실망 여지를 크게 허용하지 않습니다."
        if label == "INSUFFICIENT DATA":
            return "핵심 판단을 내리기에는 확인 가능한 데이터가 부족합니다."
        return "현재 산출 기준에서는 품질과 가격을 함께 검토해야 합니다."
    if "EXPENSIVE" in label:
        return (
            "The business shows strong profitability, but the valuation leaves less "
            "room for disappointment."
        )
    if label == "INSUFFICIENT DATA":
        return "Available evidence is not strong enough for a high-confidence investment view."
    return (
        "The current evidence supports a balanced valuation review rather than a categorical call."
    )


def investment_summary(label: str, value: dict[str, Any], language: str) -> str:
    conclusion = str(value.get("conclusion") or "INSUFFICIENT DATA")
    if language == "ko":
        return (
            f"YouRich 결론은 {label}입니다. 가치평가 산출 결론은 {conclusion}이며, "
            "확정적 매수/매도 판단은 제공하지 않습니다."
        )
    return (
        f"YouRich's conclusion is {label}. The deterministic valuation result is "
        f"{conclusion}; this is not a guaranteed buy or sell instruction."
    )
