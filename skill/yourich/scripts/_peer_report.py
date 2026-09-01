from __future__ import annotations

from typing import Any

from _report_format import markdown_table


def render_peer_markdown(result: dict[str, Any], language: str = "en") -> str:
    labels = report_labels(language)
    lines = [
        f"# {result.get('company')} · {result.get('ticker')}",
        "",
        f"## {labels['industry']}",
        industry_text(result),
        "",
        f"## {labels['peers']}",
        markdown_table(peer_rows(result, language)),
        "",
        f"## {labels['glance']}",
        markdown_table(glance_rows(result, language)),
        "",
        f"## {labels['valuation']}",
        markdown_table(valuation_rows(result, language)),
        "",
        f"## {labels['justified']}",
        str(result.get("premium_justification", {}).get("status", "INSUFFICIENT_EVIDENCE")),
        "",
        f"## {labels['business']}",
        markdown_table(business_rows(result, language)),
        "",
        f"## {labels['risks']}",
        risk_text(result, language),
        "",
        f"## {labels['changes']}",
        str(result.get("industry_changes", {}).get("status", "INSUFFICIENT_EVIDENCE")),
        "",
        f"## {labels['conclusion']}",
        conclusion_text(result, language),
        "",
        f"## {labels['data']}",
        warning_text(result),
    ]
    return "\n".join(lines).strip() + "\n"


def industry_text(result: dict[str, Any]) -> str:
    industry = result.get("industry", {})
    return (
        f"{industry.get('sector', 'Unknown')} / {industry.get('industry', 'Unknown')} "
        f"({industry.get('confidence', 'LOW')})"
    )


def peer_rows(result: dict[str, Any], language: str) -> list[dict[str, str]]:
    labels = (
        ("티커", "비교가능성", "선정 기준")
        if language == "ko"
        else ("Ticker", "Comparability", "Reason")
    )
    return [
        {
            labels[0]: str(item.get("ticker")),
            labels[1]: str(item.get("comparability_status")),
            labels[2]: str(item.get("reason_selected")),
        }
        for item in result.get("peer_set", {}).get("candidates", [])
    ]


def glance_rows(result: dict[str, Any], language: str) -> list[dict[str, str]]:
    label = "항목" if language == "ko" else "Item"
    value = "값" if language == "ko" else "Value"
    return [
        {label: "Peer set quality", value: str(result.get("peer_set", {}).get("quality"))},
        {
            label: "Premium status",
            value: str(result.get("premium_justification", {}).get("status")),
        },
        {label: "Industry signal", value: str(result.get("industry_changes", {}).get("status"))},
    ]


def valuation_rows(result: dict[str, Any], language: str) -> list[dict[str, str]]:
    label = "지표" if language == "ko" else "Metric"
    company = str(result.get("ticker") or "Company")
    peer = "동종기업 중앙값" if language == "ko" else "Peer Median"
    premium = "프리미엄" if language == "ko" else "Premium"
    rows = [
        {
            label: str(item.get("metric")),
            company: str(item.get("company")),
            peer: str(item.get("peer_median")),
            premium: str(item.get("premium_percent")),
        }
        for item in result.get("relative_valuation", [])
        if isinstance(item, dict)
    ]
    return rows or [
        {label: "valuation", company: "Unavailable", peer: "Unavailable", premium: "Unavailable"}
    ]


def business_rows(result: dict[str, Any], language: str) -> list[dict[str, str]]:
    ticker = "티커" if language == "ko" else "Ticker"
    model = "사업 구조" if language == "ko" else "Business Model"
    evidence = "근거" if language == "ko" else "Evidence"
    return [
        {
            ticker: str(item.get("ticker")),
            model: str(item.get("business_model")),
            evidence: str(item.get("evidence")),
        }
        for item in result.get("business_comparison", [])
    ]


def risk_text(result: dict[str, Any], language: str) -> str:
    risks = result.get("industry_risks", {})
    shared = ", ".join(str(item) for item in risks.get("industry_wide", []))
    if shared:
        return shared
    return "근거가 부족합니다." if language == "ko" else "Insufficient evidence"


def conclusion_text(result: dict[str, Any], language: str) -> str:
    status = str(result.get("premium_justification", {}).get("status", "INSUFFICIENT_EVIDENCE"))
    if language == "ko":
        return f"프리미엄 판단은 {status}입니다. 투자 행동 지시는 제공하지 않습니다."
    return f"Premium assessment is {status}. YouRich does not provide action instructions."


def warning_text(result: dict[str, Any]) -> str:
    warnings = result.get("warnings", [])
    return (
        "\n".join(f"- {warning}" for warning in warnings) if warnings else "No material warnings."
    )


def report_labels(language: str) -> dict[str, str]:
    if language == "ko":
        return {
            "industry": "산업 분류",
            "peers": "비교 기업",
            "glance": "한눈에 보기",
            "valuation": "가치평가",
            "justified": "현재 프리미엄은 정당한가",
            "business": "사업 구조 차이",
            "risks": "공통 산업 위험",
            "changes": "최근 산업 변화",
            "conclusion": "결론",
            "data": "데이터 및 근거",
        }
    return {
        "industry": "Industry Classification",
        "peers": "Peer Companies",
        "glance": "At A Glance",
        "valuation": "Valuation",
        "justified": "Is The Premium Justified",
        "business": "Business Structure Differences",
        "risks": "Shared Industry Risks",
        "changes": "Recent Industry Changes",
        "conclusion": "Conclusion",
        "data": "Data And Evidence",
    }
