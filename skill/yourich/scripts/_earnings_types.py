from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

EARNINGS_MODES: Final = ("earnings", "guidance")
GUIDANCE_CHANGE_STATUSES: Final = (
    "RAISED",
    "LOWERED",
    "REITERATED",
    "NEW",
    "WITHDRAWN",
    "NOT_COMPARABLE",
    "INSUFFICIENT_EVIDENCE",
)
GUIDANCE_ACTUAL_STATUSES: Final = (
    "ABOVE_GUIDANCE",
    "WITHIN_GUIDANCE",
    "BELOW_GUIDANCE",
    "NOT_COMPARABLE",
)
THESIS_CHANGE_STATUSES: Final = (
    "STRENGTHENED",
    "SLIGHTLY_STRENGTHENED",
    "UNCHANGED",
    "SLIGHTLY_WEAKENED",
    "WEAKENED",
    "INSUFFICIENT_EVIDENCE",
)


@dataclass(frozen=True, slots=True)
class EarningsRequest:
    ticker: str
    history: int = 2
    deterministic_financials: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class EarningsDocument:
    ticker: str
    company: str
    document_type: str
    published_at: str
    period_end: str | None
    source_url: str
    source_type: str
    title: str
    retrieved_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company": self.company,
            "document_type": self.document_type,
            "published_at": self.published_at,
            "period_end": self.period_end,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "title": self.title,
            "retrieved_at": self.retrieved_at,
        }


@dataclass(frozen=True, slots=True)
class EarningsMetric:
    metric: str
    value: str
    unit: str
    source: str
    source_type: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "source_type": self.source_type,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class GuidanceItem:
    metric: str
    period: str
    low: str | None
    high: str | None
    midpoint: str | None
    unit: str
    source: str
    status: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "period": self.period,
            "low": self.low,
            "high": self.high,
            "midpoint": self.midpoint,
            "unit": self.unit,
            "source": self.source,
            "status": self.status,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class ManagementStatement:
    statement: str
    speaker: str | None
    role: str | None
    category: str
    source: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "speaker": self.speaker,
            "role": self.role,
            "category": self.category,
            "source": self.source,
            "evidence": self.evidence,
        }


@dataclass(frozen=True, slots=True)
class EarningsRelease:
    document: EarningsDocument
    reported_metrics: dict[str, EarningsMetric]
    guidance: list[GuidanceItem]
    management_commentary: list[ManagementStatement]
    evidence: list[dict[str, Any]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "document": self.document.to_dict(),
            "reported_metrics": {
                key: metric.to_dict() for key, metric in self.reported_metrics.items()
            },
            "guidance": [item.to_dict() for item in self.guidance],
            "management_commentary": [item.to_dict() for item in self.management_commentary],
            "evidence": self.evidence,
            "warnings": self.warnings,
        }
