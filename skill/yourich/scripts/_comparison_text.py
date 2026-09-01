from __future__ import annotations

from typing import Any

from _report_format import basis_label, korean_basis_label


def bullet_list(items: Any, language: str, fallback: str) -> str:
    if not isinstance(items, list) or not items:
        return fallback
    return "\n".join(
        f"- {difference_text(item, language)}" for item in items if isinstance(item, dict)
    )


def scenario_text(entry: dict[str, Any], labels: dict[str, str], language: str) -> str:
    bull = point_list(entry.get("bull_case"))
    bear = point_list(entry.get("bear_case"))
    if not bull and not bear:
        return labels["scenario_body"]
    lines = [labels["bull_case"], *[f"- {point_text(point, language)}" for point in bull]]
    lines.extend(["", labels["bear_case"], *[f"- {point_text(point, language)}" for point in bear]])
    return "\n".join(lines)


def point_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def change_text(change: dict[str, Any], language: str) -> str:
    ticker = str(change.get("ticker", ""))
    status = str(change.get("change", ""))
    if language == "ko":
        labels = {
            "CHANGED": "위험 요인 문구 변화가 감지되었습니다.",
            "NO_MATERIAL_TEXT_CHANGE": "위험 요인 문구 변화가 감지되지 않았습니다.",
        }
        return f"{ticker}: {labels.get(status, status)}"
    return f"{ticker}: {status.replace('_', ' ').title()}"


def difference_text(item: dict[str, Any], language: str) -> str:
    kind = str(item.get("kind", ""))
    leader = str(item.get("leader", ""))
    laggard = str(item.get("laggard", ""))
    if language == "ko":
        return korean_difference(kind, leader, laggard)
    return english_difference(kind, leader, laggard)


def korean_difference(kind: str, leader: str, laggard: str) -> str:
    labels = {
        "net_margin": f"{leader}는 순이익률에서 {laggard}보다 앞섭니다.",
        "fcf_margin": f"{leader}는 잉여현금흐름 마진에서 {laggard}보다 앞섭니다.",
        "pe": f"{laggard}는 P/E 부담이 {leader}보다 높습니다.",
        "fcf_yield": f"{leader}는 잉여현금흐름 수익률에서 {laggard}보다 앞섭니다.",
        "evidence_quality": f"{leader}는 {laggard}보다 사업 경쟁력 근거가 더 강합니다.",
        "insufficient_evidence": "비교 가능한 사업 근거가 부족합니다.",
    }
    return labels.get(kind, f"{leader}와 {laggard}의 비교 근거를 확인해야 합니다.")


def english_difference(kind: str, leader: str, laggard: str) -> str:
    labels = {
        "net_margin": f"{leader} leads {laggard} on net margin.",
        "fcf_margin": f"{leader} leads {laggard} on free-cash-flow margin.",
        "pe": f"{laggard} carries a higher P/E burden than {leader}.",
        "fcf_yield": f"{leader} leads {laggard} on free-cash-flow yield.",
        "evidence_quality": f"{leader} has stronger business evidence than {laggard}.",
        "insufficient_evidence": "Comparable business evidence is insufficient.",
    }
    return labels.get(kind, f"{leader} and {laggard} need additional comparison evidence.")


def point_text(point: str, language: str) -> str:
    if language != "ko":
        return point
    labels = {
        "Profitability is already strong on reported financial metrics.": (
            "공시 기반 재무 지표에서 수익성이 이미 강합니다."
        ),
        "Free cash flow generation supports the upside case.": (
            "잉여현금흐름 창출력이 상승 시나리오를 뒷받침합니다."
        ),
        "Cash-flow yield is stronger than the comparison peer.": (
            "비교 대상보다 현금흐름 수익률이 높습니다."
        ),
        "P/E multiple already reflects elevated expectations.": (
            "P/E 배수에는 이미 높은 기대가 반영되어 있습니다."
        ),
    }
    if point.endswith("_risk"):
        return risk_label(point, language)
    return labels.get(point, point)


def risk_label(value: str, language: str) -> str:
    labels = {
        "debt_risk": "부채 위험",
        "liquidity_risk": "유동성 위험",
        "negative_equity": "자본잠식 위험",
        "earnings_deterioration": "이익 악화 위험",
        "fcf_deterioration": "잉여현금흐름 악화 위험",
        "margin_deterioration": "마진 악화 위험",
        "valuation_risk": "가치평가 위험",
        "share_dilution": "주식 희석 위험",
    }
    if language == "ko":
        return labels.get(value, value.replace("_", " "))
    return value.replace("_", " ")


def comparison_basis_label(value: Any, language: str) -> str:
    raw = str(value)
    if raw == "unknown":
        return "알 수 없음" if language == "ko" else raw
    parts = [part for part in raw.split("|") if part]
    if language != "ko":
        return " + ".join(basis_label(part) for part in parts)
    return " + ".join(korean_basis_label(basis_label(part)) for part in parts)
