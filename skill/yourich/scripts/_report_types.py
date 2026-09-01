from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from _core import to_jsonable


@dataclass(frozen=True, slots=True)
class ReportMetric:
    name: str
    value: str
    meaning: str
    kind: str
    basis: str | None
    source: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "meaning": self.meaning,
            "type": self.kind,
            "basis": self.basis,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ReportSection:
    key: str
    title: str
    body: str
    rows: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "title": self.title, "body": self.body, "rows": self.rows}


@dataclass(frozen=True, slots=True)
class InvestmentReport:
    company: str
    ticker: str
    language: str
    overall_label: str
    overall_summary: str
    sections: list[ReportSection]
    key_metrics: list[ReportMetric]
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "ticker": self.ticker,
            "language": self.language,
            "overall_assessment": {
                "label": self.overall_label,
                "summary": self.overall_summary,
            },
            "key_metrics": [metric.to_dict() for metric in self.key_metrics],
            "sections": [section.to_dict() for section in self.sections],
            "raw": to_jsonable(self.raw),
        }


HEADINGS: dict[str, dict[str, str]] = {
    "en": {
        "overall": "Overall Assessment",
        "glance": "At a Glance",
        "summary": "Investment Summary",
        "metrics": "Key Metrics",
        "business": "Business Quality",
        "financial": "Financial Quality",
        "valuation": "Valuation",
        "risks": "Key Risks",
        "bull": "Bull Case",
        "bear": "Bear Case",
        "changed": "What Changed",
        "conclusion": "Conclusion",
        "quality": "Data Quality & Methodology",
    },
    "ko": {
        "overall": "종합 판단",
        "glance": "한눈에 보기",
        "summary": "투자 요약",
        "metrics": "핵심 지표",
        "business": "사업 경쟁력",
        "financial": "재무 상태",
        "valuation": "가치평가",
        "risks": "주요 위험",
        "bull": "상승 시나리오",
        "bear": "하락 시나리오",
        "changed": "변화 요약",
        "conclusion": "결론",
        "quality": "데이터 및 산출 기준",
    },
}


SECTION_ORDER = (
    "overall",
    "glance",
    "summary",
    "metrics",
    "business",
    "financial",
    "valuation",
    "risks",
    "bull",
    "bear",
    "changed",
    "conclusion",
    "quality",
)
