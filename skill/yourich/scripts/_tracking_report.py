from __future__ import annotations

from typing import Any


def render_tracking_markdown(result: dict[str, Any], language: str = "en") -> str:
    return render_ko(result) if language.lower().startswith("ko") else render_en(result)


def render_ko(result: dict[str, Any]) -> str:
    lines = [
        f"# {result.get('ticker')} Research Update",
        "",
        "## 지난 분석 이후",
        "",
        "### 핵심 변화",
        "",
    ]
    lines.extend(change_lines(result, language="ko"))
    lines.extend(["", "### 투자 논리", "", thesis_rows(result, language="ko")])
    lines.extend(
        [
            "",
            "### 종합 변화",
            str(result.get("thesis_change", {}).get("overall_change", "INSUFFICIENT_EVIDENCE")),
            "",
            "### 계속 볼 항목",
            "",
        ]
    )
    lines.extend(watch_lines(result))
    lines.extend(["", "### 데이터 기준", *basis_lines(result, language="ko")])
    return "\n".join(lines).strip() + "\n"


def render_en(result: dict[str, Any]) -> str:
    lines = [
        f"# {result.get('ticker')} Research Update",
        "",
        "## Since Previous Analysis",
        "",
        "### Key Changes",
        "",
    ]
    lines.extend(change_lines(result, language="en"))
    lines.extend(["", "### Thesis", "", thesis_rows(result, language="en")])
    lines.extend(
        [
            "",
            "### Overall Change",
            str(result.get("thesis_change", {}).get("overall_change", "INSUFFICIENT_EVIDENCE")),
            "",
            "### Watch Variables",
            "",
        ]
    )
    lines.extend(watch_lines(result))
    lines.extend(["", "### Data Basis", *basis_lines(result, language="en")])
    return "\n".join(lines).strip() + "\n"


def change_lines(result: dict[str, Any], language: str) -> list[str]:
    changes = result.get("changes", [])
    if not isinstance(changes, list) or not changes:
        return ["= NO_MATERIAL_CHANGE"]
    return [
        f"{marker(str(item.get('direction')))} {change_label(item, language)}"
        for item in changes[:8]
    ]


def marker(direction: str) -> str:
    if direction in {"IMPROVED", "NEW"}:
        return "+"
    if direction in {"WORSENED", "REMOVED"}:
        return "-"
    return "="


def change_label(item: dict[str, Any], language: str) -> str:
    field = str(item.get("field", "")).replace("_", " ")
    direction = str(item.get("direction", ""))
    if language == "ko":
        labels = {
            "revenue_growth": "매출 성장",
            "guidance_direction": "가이던스",
            "required_fcf_cagr": "요구 FCF 성장률",
            "pe": "P/E",
            "peer_set": "동종기업 구성",
        }
        field = labels.get(str(item.get("field")), field)
    return f"{field}: {direction}"


def thesis_rows(result: dict[str, Any], language: str) -> str:
    dimensions = result.get("thesis_change", {}).get("dimensions", {})
    if not isinstance(dimensions, dict) or not dimensions:
        return "INSUFFICIENT_EVIDENCE"
    labels = {
        "business_quality": ("Business Quality", "사업 경쟁력"),
        "financial_quality": ("Financial Quality", "재무 상태"),
        "growth_outlook": ("Growth Outlook", "성장 전망"),
        "valuation_attractiveness": ("Valuation Attractiveness", "가치평가 매력"),
        "risk_level": ("Risk", "위험"),
    }
    rows = []
    for key, value in dimensions.items():
        label = labels.get(str(key), (str(key), str(key)))[1 if language == "ko" else 0]
        rows.append(f"- {label}: {value}")
    return "\n".join(rows)


def watch_lines(result: dict[str, Any]) -> list[str]:
    variables = result.get("watch_variables", [])
    if not isinstance(variables, list) or not variables:
        return ["- TRACKING_DATA_INCOMPLETE"]
    return [f"- {item.get('name')}" for item in variables if isinstance(item, dict)]


def basis_lines(result: dict[str, Any], language: str) -> list[str]:
    previous = result.get("previous_snapshot")
    current = result.get("current_snapshot")
    previous_label = "이전 분석" if language == "ko" else "Previous analysis"
    current_label = "현재 분석" if language == "ko" else "Current analysis"
    return [
        f"- {previous_label}: {snapshot_date(previous)}",
        f"- {current_label}: {snapshot_date(current)}",
    ]


def snapshot_date(value: Any) -> str:
    if isinstance(value, dict) and value.get("created_at") is not None:
        return str(value["created_at"])
    return "Unavailable"
