from __future__ import annotations


def risk_row(risk: str, status: str, language: str) -> dict[str, str]:
    if language != "ko":
        return {"Risk": risk, "Status": status}
    return {"위험": korean_risk_label(risk), "상태": korean_status_label(status)}


def scenario_row(point: str, language: str) -> dict[str, str]:
    if language != "ko":
        return {"Point": point}
    labels = {
        "Profitability and cash generation remain durable": "수익성과 현금창출력이 유지됩니다.",
        "Valuation multiple compresses": "가치평가 배수가 낮아집니다.",
        "Triggered financial risks worsen": "감지된 재무 위험이 악화됩니다.",
        "Valuation leaves room for upside": "가치평가가 상승 여지를 남깁니다.",
    }
    return {"요인": labels.get(point, point)}


def korean_area_label(label: str) -> str:
    labels = {
        "Business Quality": "사업 경쟁력",
        "Profitability": "수익성",
        "Financial Health": "재무 건전성",
        "Valuation": "가치평가",
        "Risk": "위험",
        "Evidence Quality": "근거 품질",
    }
    return labels.get(label, label)


def korean_assessment_label(label: str) -> str:
    labels = {
        "Insufficient evidence": "근거 부족",
        "Insufficient data": "데이터 부족",
        "Strong": "강함",
        "Evidence-linked": "공시 근거 있음",
        "Very Strong": "매우 강함",
        "Moderate": "보통",
        "Weak": "약함",
        "Stressed": "부담 높음",
        "Healthy": "건전",
        "Tight": "빠듯함",
        "Fairly Valued": "적정 가치",
        "Attractive Valuation": "저평가 매력",
        "Attractive": "저평가",
        "Expensive": "고평가",
        "High": "높음",
        "Elevated": "상승",
        "Medium": "보통",
        "Low": "낮음",
    }
    return labels.get(label, label)


def korean_risk_label(label: str) -> str:
    labels = {"Quantitative checks": "정량 위험 점검"}
    return labels.get(label, label)


def korean_status_label(label: str) -> str:
    labels = {"Triggered": "감지됨", "No triggered risk checks": "감지된 위험 없음"}
    return labels.get(label, label)
