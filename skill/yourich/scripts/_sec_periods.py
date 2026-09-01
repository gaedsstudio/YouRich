from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import pairwise

from _core import ZERO
from _sec_types import (
    FORM_RANK,
    TTM_QUARTERS,
    Fact,
    FieldSelection,
    PeriodClass,
    next_day,
    period_overlaps,
)


@dataclass(frozen=True, slots=True)
class YearFacts:
    reported_quarters: dict[str, Fact]
    ytd_6m: Fact | None
    ytd_9m: Fact | None
    annual: Fact | None


def reconstruct_discrete_quarters(facts: list[Fact]) -> list[Fact]:
    by_year = facts_by_year(facts)
    quarters: list[Fact] = []
    for yearly in by_year.values():
        quarters.extend(yearly.reported_quarters.values())
        quarters.extend(derived_quarters(yearly))
    return dedupe_quarters(quarters)


def select_ttm(facts: list[Fact]) -> FieldSelection:
    quarters = reconstruct_discrete_quarters(facts)
    sequence = sorted(quarters, key=sort_key, reverse=True)[:TTM_QUARTERS]
    if len(sequence) != TTM_QUARTERS or has_period_issue(sequence):
        return FieldSelection(
            None, "ttm", "LOW", tuple(sequence), restated=False, previous_value=None
        )
    value = sum((fact.value for fact in sequence), ZERO)
    confidence = min_confidence(sequence)
    return FieldSelection(
        value,
        "ttm",
        confidence,
        tuple(sequence),
        restated=False,
        previous_value=None,
    )


def is_current_enough(ttm: FieldSelection, annual: FieldSelection) -> bool:
    if annual.value is None or not annual.facts:
        return True
    if not ttm.facts:
        return False
    latest_ttm_end = max(fact.end for fact in ttm.facts)
    return latest_ttm_end >= annual.facts[0].end


def facts_by_year(facts: list[Fact]) -> dict[int, YearFacts]:
    by_year: dict[int, YearFacts] = {}
    for fact in facts:
        current = by_year.setdefault(fact.fy, YearFacts({}, None, None, None))
        match fact.period_class:
            case PeriodClass.QUARTER:
                current.reported_quarters[fact.fp] = fact
            case PeriodClass.YTD_6M:
                by_year[fact.fy] = replace(current, ytd_6m=better_fact(current.ytd_6m, fact))
            case PeriodClass.YTD_9M:
                by_year[fact.fy] = replace(current, ytd_9m=better_fact(current.ytd_9m, fact))
            case PeriodClass.ANNUAL:
                by_year[fact.fy] = replace(current, annual=better_fact(current.annual, fact))
            case PeriodClass.OTHER_DURATION | PeriodClass.INSTANT | PeriodClass.DERIVED_TTM:
                continue
    return by_year


def better_fact(current: Fact | None, candidate: Fact) -> Fact:
    if current is None:
        return candidate
    return sorted([current, candidate], key=sort_key)[-1]


def derived_quarters(yearly: YearFacts) -> list[Fact]:
    derived: list[Fact] = []
    q1 = yearly.reported_quarters.get("Q1")
    if yearly.ytd_6m is not None and q1 is not None and "Q2" not in yearly.reported_quarters:
        derived.append(derive_quarter(yearly.ytd_6m, q1, "Q2"))
    if (
        yearly.ytd_9m is not None
        and yearly.ytd_6m is not None
        and "Q3" not in yearly.reported_quarters
    ):
        derived.append(derive_quarter(yearly.ytd_9m, yearly.ytd_6m, "Q3"))
    if (
        yearly.annual is not None
        and yearly.ytd_9m is not None
        and "Q4" not in yearly.reported_quarters
    ):
        derived.append(derive_quarter(yearly.annual, yearly.ytd_9m, "Q4"))
    return [fact for fact in derived if fact.start is not None]


def derive_quarter(later: Fact, earlier: Fact, fp: str) -> Fact:
    start = next_day(earlier.end)
    return Fact(
        field=later.field,
        taxonomy=later.taxonomy,
        concept=later.concept,
        unit=later.unit,
        value=later.value - earlier.value,
        fy=later.fy,
        fp=fp,
        form=later.form,
        filed=later.filed,
        end=later.end,
        start=start,
        frame=None,
        accn=later.accn,
        concept_rank=later.concept_rank,
        source_kind="derived_quarter",
        derived_from=(earlier.period_label, later.period_label),
    )


def dedupe_quarters(facts: list[Fact]) -> list[Fact]:
    latest: dict[tuple[str, str, str], Fact] = {}
    for fact in sorted(facts, key=sort_key):
        latest[(fact.unit, fact.fp, fact.end)] = fact
    return sorted(latest.values(), key=sort_key, reverse=True)


def has_period_issue(facts: list[Fact]) -> bool:
    labels = [fact.period_label for fact in facts]
    if len(labels) != len(set(labels)):
        return True
    sorted_facts = sorted(facts, key=lambda fact: fact.start or fact.end)
    return any(has_bad_boundary(first, second) for first, second in pairwise(sorted_facts))


def has_bad_boundary(first: Fact, second: Fact) -> bool:
    if period_overlaps(first, second):
        return True
    return first.start is None or second.start != next_day(first.end)


def sort_key(fact: Fact) -> tuple[str, str, int, int]:
    return (fact.end, fact.filed, -FORM_RANK[fact.form], -fact.concept_rank)


def min_confidence(facts: list[Fact]) -> str:
    values = {fact.confidence for fact in facts}
    if "LOW" in values:
        return "LOW"
    if "MEDIUM" in values:
        return "MEDIUM"
    return "HIGH"
