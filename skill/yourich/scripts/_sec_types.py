from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, TypeAlias

Concept: TypeAlias = tuple[str, str, tuple[str, ...]]
MEDIUM_CONCEPT_RANK = 2
TTM_QUARTERS = 4
FORM_RANK = {"10-K": 0, "10-Q": 1, "10-K/A": 2, "10-Q/A": 3}


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

    @property
    def period_key(self) -> tuple[str, str, str | None, str]:
        return (self.concept, self.unit, self.frame, self.end)

    @property
    def is_annual(self) -> bool:
        return self.fp == "FY" or self.form in {"10-K", "10-K/A"}

    @property
    def is_quarter(self) -> bool:
        return self.fp in {"Q1", "Q2", "Q3", "Q4"} and self.form in {"10-Q", "10-Q/A"}

    @property
    def confidence(self) -> str:
        if self.concept_rank == 0 and self.unit in {"USD", "USD/shares", "shares"}:
            return "HIGH"
        if self.concept_rank <= MEDIUM_CONCEPT_RANK:
            return "MEDIUM"
        return "LOW"


@dataclass(frozen=True, slots=True)
class FieldSelection:
    value: Decimal | None
    basis: str
    confidence: str
    facts: tuple[Fact, ...]
    restated: bool
    previous_value: Decimal | None

    def metadata(self) -> dict[str, Any] | None:
        if not self.facts:
            return None
        fact = self.facts[0]
        return {
            "concept": fact.concept,
            "taxonomy": fact.taxonomy,
            "unit": fact.unit,
            "fy": fact.fy,
            "fp": fact.fp,
            "form": fact.form,
            "filed": fact.filed,
            "period_end": fact.end,
            "start": fact.start,
            "frame": fact.frame,
            "accn": fact.accn,
            "basis": self.basis,
            "confidence": self.confidence,
            "amended": fact.form.endswith("/A"),
            "restated": self.restated,
            "previous_value": self.previous_value,
        }

    def source(self) -> str | None:
        if not self.facts:
            return None
        fact = self.facts[0]
        return f"SEC:{fact.taxonomy}:{fact.concept}:{fact.unit}:{self.basis}:{fact.end}"
