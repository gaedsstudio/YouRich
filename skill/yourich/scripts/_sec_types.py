from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, TypeAlias

Concept: TypeAlias = tuple[str, str, tuple[str, ...]]
MEDIUM_CONCEPT_RANK = 2
TTM_QUARTERS = 4
FORM_RANK = {"10-K": 0, "10-Q": 1, "10-K/A": 2, "10-Q/A": 3}
QUARTER_DAY_MIN = 70
QUARTER_DAY_MAX = 120
YTD_6M_DAY_MIN = 150
YTD_6M_DAY_MAX = 220
YTD_9M_DAY_MIN = 240
YTD_9M_DAY_MAX = 310
ANNUAL_DAY_MIN = 330


class PeriodClass(StrEnum):
    QUARTER = "QUARTER"
    YTD_6M = "YTD_6M"
    YTD_9M = "YTD_9M"
    ANNUAL = "ANNUAL"
    OTHER_DURATION = "OTHER_DURATION"
    INSTANT = "INSTANT"
    DERIVED_TTM = "DERIVED_TTM"


@dataclass(frozen=True, slots=True)
class Fact:
    field: str
    taxonomy: str
    concept: str
    unit: str
    value: Decimal
    fy: int
    fp: str
    form: str
    filed: str
    end: str
    start: str | None
    frame: str | None
    accn: str | None
    concept_rank: int
    source_kind: str = "reported"
    derived_from: tuple[str, ...] = ()

    @property
    def period_key(self) -> tuple[str, str, str | None, str]:
        return (self.concept, self.unit, self.start, self.end)

    @property
    def is_annual(self) -> bool:
        return self.period_class == PeriodClass.ANNUAL

    @property
    def is_quarter(self) -> bool:
        return self.period_class == PeriodClass.QUARTER

    @property
    def period_class(self) -> PeriodClass:
        if self.start is None:
            return PeriodClass.INSTANT
        if self.source_kind != "reported":
            return PeriodClass.QUARTER
        days = duration_days(self.start, self.end)
        if self.fp == "FY" or self.form in {"10-K", "10-K/A"}:
            return annual_period_class(days)
        return quarterly_period_class(self.fp, days)

    @property
    def confidence(self) -> str:
        if self.concept_rank == 0 and self.unit in {"USD", "USD/shares", "shares"}:
            return "HIGH"
        if self.concept_rank <= MEDIUM_CONCEPT_RANK:
            return "MEDIUM"
        return "LOW"

    @property
    def period_label(self) -> str:
        if self.start is None:
            return self.end
        return f"{self.start}:{self.end}"


@dataclass(frozen=True, slots=True)
class FieldSelection:
    value: Decimal | None
    basis: str
    confidence: str
    facts: tuple[Fact, ...]
    restated: bool
    previous_value: Decimal | None
    coverage: str = "complete"
    period_start: str | None = None
    period_end: str | None = None
    source_fact_items: tuple[Fact, ...] = ()

    def metadata(self) -> dict[str, Any] | None:
        if not self.facts:
            return None
        fact = self.facts[0]
        period_start = self.period_start or fact.start
        period_end = self.period_end or fact.end
        source_items = self.source_fact_items or self.facts
        derived_from = sorted({source for item in self.facts for source in item.derived_from})
        if not derived_from and self.basis == "ttm":
            derived_from = [item.period_label for item in sorted(source_items, key=source_fact_key)]
        return {
            "concept": fact.concept,
            "taxonomy": fact.taxonomy,
            "unit": fact.unit,
            "fy": fact.fy,
            "fp": fact.fp,
            "form": fact.form,
            "filed": fact.filed,
            "period_start": period_start,
            "period_end": period_end,
            "start": period_start,
            "frame": fact.frame,
            "accn": fact.accn,
            "basis": self.basis,
            "period_class": "DERIVED_TTM" if self.basis == "ttm" else str(fact.period_class),
            "source_kind": "derived_ttm" if self.basis == "ttm" else fact.source_kind,
            "component_periods": [
                item.period_label for item in sorted(source_items, key=source_fact_key)
            ],
            "derived_from": derived_from,
            "coverage": self.coverage,
            "source_facts": [
                source_fact(item) for item in sorted(source_items, key=source_fact_key)
            ],
            "confidence": self.confidence,
            "amended": fact.form.endswith("/A"),
            "restated": self.restated,
            "previous_value": self.previous_value,
        }

    def source(self) -> str | None:
        if not self.facts:
            return None
        fact = self.facts[0]
        period_end = self.period_end or fact.end
        return f"SEC:{fact.taxonomy}:{fact.concept}:{fact.unit}:{self.basis}:{period_end}"


def source_fact(fact: Fact) -> dict[str, Any]:
    return {
        "concept": fact.concept,
        "unit": fact.unit,
        "fy": fact.fy,
        "fp": fact.fp,
        "form": fact.form,
        "filed": fact.filed,
        "period_start": fact.start,
        "period_end": fact.end,
        "value": fact.value,
        "source_kind": fact.source_kind,
        "accn": fact.accn,
    }


def source_fact_key(fact: Fact) -> tuple[str, str, str]:
    return (fact.start or "", fact.end, fact.filed)


def duration_days(start: str, end: str) -> int | None:
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    except ValueError:
        return None


def duration_between(days: int | None, minimum: int, maximum: int) -> bool:
    return days is not None and minimum <= days <= maximum


def annual_period_class(days: int | None) -> PeriodClass:
    if days is None or days >= ANNUAL_DAY_MIN:
        return PeriodClass.ANNUAL
    return PeriodClass.OTHER_DURATION


def quarterly_period_class(fp: str, days: int | None) -> PeriodClass:
    if fp == "Q1" and duration_between(days, QUARTER_DAY_MIN, QUARTER_DAY_MAX):
        return PeriodClass.QUARTER
    if fp == "Q2" and duration_between(days, YTD_6M_DAY_MIN, YTD_6M_DAY_MAX):
        return PeriodClass.YTD_6M
    if fp == "Q3" and duration_between(days, YTD_9M_DAY_MIN, YTD_9M_DAY_MAX):
        return PeriodClass.YTD_9M
    if fp in {"Q1", "Q2", "Q3", "Q4"} and duration_between(days, QUARTER_DAY_MIN, QUARTER_DAY_MAX):
        return PeriodClass.QUARTER
    return PeriodClass.OTHER_DURATION


def next_day(day: str) -> str | None:
    try:
        return (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    except ValueError:
        return None


def period_overlaps(first: Fact, second: Fact) -> bool:
    if first.start is None or second.start is None:
        return False
    return first.start <= second.end and second.start <= first.end
