from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from _core import decimal_or_none

if TYPE_CHECKING:
    from _report_types import InvestmentReport, ReportMetric


def render_markdown(report: InvestmentReport) -> str:
    lines = [
        f"# {report.company} · {report.ticker}",
        "",
        f"## {report.sections[0].title}",
        report.overall_label,
        "",
        report.overall_summary,
    ]
    for section in report.sections[1:]:
        lines.extend(["", f"## {section.title}"])
        if section.body:
            lines.extend(["", section.body])
        if section.rows:
            lines.extend(["", markdown_table(section.rows)])
    return "\n".join(lines).strip() + "\n"


def markdown_table(rows: list[dict[str, str]]) -> str:
    columns = list(rows[0])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(row.get(column, "") for column in columns) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def metric_rows(metrics: list[ReportMetric]) -> list[dict[str, str]]:
    return [
        {"Metric": metric.name, "Value": metric.value, "What it means": metric.meaning}
        for metric in metrics
    ]


def valuation_row(metrics: dict[str, Any], label: str, key: str) -> dict[str, str]:
    metric = metrics.get(key, {})
    return {
        "Metric": label,
        "Value": multiple_or_percent(metric.get("value"), key),
        "Basis": basis_label(metric.get("basis")),
    }


def metadata_for(company: dict[str, Any], key: str) -> dict[str, Any]:
    metadata = company.get("fact_metadata", {}).get(key, {})
    return metadata if isinstance(metadata, dict) else {}


def money(value: Any) -> str:
    amount = decimal_or_none(value)
    if amount is None:
        return "Unavailable"
    absolute = abs(amount)
    if absolute >= Decimal("1000000000000"):
        return f"${amount / Decimal('1000000000000'):.1f}T"
    if absolute >= Decimal("1000000000"):
        return f"${amount / Decimal('1000000000'):.1f}B"
    if absolute >= Decimal("1000000"):
        return f"${amount / Decimal('1000000'):.1f}M"
    return f"${amount:.2f}"


def pct(value: Any) -> str:
    amount = decimal_or_none(value)
    return "Unavailable" if amount is None else f"{amount:.1f}%"


def number(value: Any) -> str:
    amount = decimal_or_none(value)
    return "Unavailable" if amount is None else f"{amount:.2f}"


def multiple_or_percent(value: Any, key: str) -> str:
    amount = decimal_or_none(value)
    if amount is None:
        return "Unavailable"
    return pct(value) if key.endswith("yield") else f"{amount:.1f}x"


def basis_label(value: Any) -> str:
    basis = str(value or "unavailable")
    labels = {
        "ttm": "TTM",
        "latest_annual": "Latest annual",
        "latest_snapshot": "Latest snapshot",
        "market_snapshot": "Market snapshot",
        "market_quote": "Market quote",
        "unavailable": "Unavailable",
    }
    return labels.get(basis, basis.replace("_", " ").title())


def meaning_for_basis(meaning: str, basis: Any) -> str:
    label = basis_label(basis)
    if label == "TTM":
        return meaning.replace("selected basis", "last 12 months")
    if label == "Latest annual":
        return meaning.replace("selected basis", "latest annual period")
    return meaning


def market_data_label(company: dict[str, Any]) -> str:
    quote = company.get("market_quote")
    if isinstance(quote, dict):
        provider = quote.get("provider")
        return str(provider) if provider else "Delayed market quote"
    return "Unavailable"


def human_warning(code: Any, company: dict[str, Any] | None = None) -> str:
    text = str(code)
    if text == "TTM_INCOMPLETE_USING_ANNUAL_FALLBACK":
        fields = annual_fallback_fields({} if company is None else company)
        suffix = "" if not fields else ": " + ", ".join(fields)
        return "Annual fallback used" + suffix
    if text == "SEC_USER_AGENT_NOT_CONFIGURED":
        return "SEC User-Agent not configured"
    return text.replace("_", " ").title()


def annual_fallback_fields(company: dict[str, Any]) -> list[str]:
    labels = {
        "revenue": "Revenue",
        "net_income": "Net income",
        "eps": "EPS",
        "free_cash_flow": "FCF",
    }
    return [
        label
        for field, label in labels.items()
        if metadata_for(company, field).get("basis") == "latest_annual"
    ]


def risk_label(value: str) -> str:
    return value.replace("_", " ").title()


def text_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def localized(text: str, language: str) -> str:
    if language != "ko":
        return text
    labels = {
        "Insufficient evidence": "근거가 부족합니다.",
        "No material warnings.": "중요 경고가 없습니다.",
        "Material risks are prioritized rather than dumped.": (
            "중요도가 높은 위험만 우선 표시합니다."
        ),
        "Scenario points are evidence-led, not recommendations.": (
            "시나리오는 추천이 아니라 근거 기반 가능성입니다."
        ),
        (
            "Profitability, liquidity, leverage, and cash generation are shown before "
            "interpretation."
        ): ("수익성, 유동성, 레버리지, 현금창출력을 먼저 표시합니다."),
        "Valuation is expensive when investors are paying a high price for current fundamentals.": (
            "현재 펀더멘털 대비 높은 가격을 지불할수록 가치평가 부담이 커집니다."
        ),
        (
            "Filing evidence is available; review linked evidence before relying on "
            "qualitative claims."
        ): ("공시 근거가 있으며, 정성 판단은 연결된 증거를 확인해야 합니다."),
    }
    return labels.get(text, text)
