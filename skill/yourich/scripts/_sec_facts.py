from __future__ import annotations

from decimal import Decimal
from typing import Any

from _core import ratio
from _sec_debt import select_total_debt
from _sec_periods import is_current_enough, select_ttm
from _sec_types import FORM_RANK, Concept, Fact, FieldSelection

INCOME_FIELDS = {
    "revenue",
    "operating_income",
    "net_income",
    "eps",
    "operating_cash_flow",
    "capital_expenditures",
}
BALANCE_FIELDS = {
    "cash",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "total_debt",
    "shareholder_equity",
    "shares_outstanding",
    "weighted_average_basic_shares",
    "weighted_average_diluted_shares",
}


def select_field(facts: Any, field: str, concepts: tuple[Concept, ...]) -> FieldSelection:
    if field == "total_debt":
        return select_total_debt(dedupe(parse_field_facts(facts, field, concepts)))
    if field in BALANCE_FIELDS or field == "eps":
        return select_first_available(facts, field, concepts)
    ttm_candidates = []
    annual_fallbacks = []
    for rank, concept in enumerate(concepts):
        raw = parse_field_facts(facts, field, (concept,), base_rank=rank)
        candidates = dedupe(raw)
        ttm = select_ttm(raw)
        annual = select_latest_annual(candidates)
        if ttm.value is not None and is_current_enough(ttm, annual):
            ttm_candidates.append(with_restatement(ttm, raw))
        annual_fallbacks.append(with_restatement(annual, raw))
    valid_annuals = [selection for selection in annual_fallbacks if selection.value is not None]
    best_annual = best_selection(valid_annuals) if valid_annuals else None
    current_ttm = [
        selection
        for selection in ttm_candidates
        if best_annual is None or is_current_enough(selection, best_annual)
    ]
    if current_ttm:
        return best_selection(current_ttm)
    if best_annual is not None:
        return best_annual
    return FieldSelection(None, "unavailable", "LOW", (), restated=False, previous_value=None)


def select_first_available(facts: Any, field: str, concepts: tuple[Concept, ...]) -> FieldSelection:
    selections = []
    for rank, concept in enumerate(concepts):
        raw = parse_field_facts(facts, field, (concept,), base_rank=rank)
        candidates = dedupe(raw)
        selection = select_from_candidates(field, candidates)
        if selection.value is not None:
            return with_restatement(selection, raw)
        if rank == 0:
            selections.append(selection)
    return (
        selections[0]
        if selections
        else FieldSelection(None, "unavailable", "LOW", (), restated=False, previous_value=None)
    )


def select_from_candidates(field: str, candidates: list[Fact]) -> FieldSelection:
    if field in BALANCE_FIELDS:
        return select_snapshot(candidates)
    if field == "eps":
        return select_eps(candidates)
    ttm = select_ttm(candidates)
    if ttm.value is not None:
        return ttm
    return select_latest_annual(candidates)


def parse_field_facts(
    facts: Any, field: str, concepts: tuple[Concept, ...], base_rank: int = 0
) -> list[Fact]:
    parsed = []
    for rank, (taxonomy, concept, units) in enumerate(concepts):
        unit_map = facts.get(taxonomy, {}).get(concept, {}).get("units", {})
        for unit in units:
            for row in unit_map.get(unit, []):
                fact = parse_fact(row, field, taxonomy, concept, unit, base_rank + rank)
                if fact is not None:
                    parsed.append(fact)
    return parsed


def parse_fact(
    row: Any,
    field: str,
    taxonomy: str,
    concept: str,
    unit: str,
    concept_rank: int,
) -> Fact | None:
    if not isinstance(row, dict) or row.get("form") not in FORM_RANK:
        return None
    value = row.get("val")
    fy = row.get("fy")
    fp = row.get("fp")
    filed = row.get("filed")
    end = row.get("end")
    if not isinstance(value, int | float | str | Decimal):
        return None
    if not isinstance(fy, int) or not isinstance(fp, str):
        return None
    if not isinstance(filed, str) or not isinstance(end, str):
        return None
    return Fact(
        field=field,
        taxonomy=taxonomy,
        concept=concept,
        unit=unit,
        value=Decimal(str(value)),
        fy=fy,
        fp=fp,
        form=str(row["form"]),
        filed=filed,
        end=end,
        start=row.get("start") if isinstance(row.get("start"), str) else None,
        frame=row.get("frame") if isinstance(row.get("frame"), str) else None,
        accn=row.get("accn") if isinstance(row.get("accn"), str) else None,
        concept_rank=concept_rank,
    )


def dedupe(facts: list[Fact]) -> list[Fact]:
    latest: dict[tuple[str, str, str | None, str, str | None], Fact] = {}
    for fact in sorted(facts, key=sort_key):
        latest[(*fact.period_key, fact.accn)] = fact
    return sorted(latest.values(), key=sort_key, reverse=True)


def select_snapshot(facts: list[Fact]) -> FieldSelection:
    if not facts:
        return FieldSelection(
            None, "latest_snapshot", "LOW", (), restated=False, previous_value=None
        )
    selected = facts[0]
    restated, previous = restatement_for(facts, selected)
    return FieldSelection(
        selected.value,
        "latest_snapshot",
        selected.confidence,
        (selected,),
        restated=restated,
        previous_value=previous,
    )


def select_latest_annual(facts: list[Fact]) -> FieldSelection:
    by_year: dict[int, Fact] = {}
    for fact in sorted([item for item in facts if item.is_annual], key=sort_key):
        by_year[fact.fy] = fact
    annual = sorted(by_year.values(), key=sort_key, reverse=True)
    if not annual:
        return FieldSelection(
            None,
            "latest_annual",
            "LOW",
            (),
            restated=False,
            previous_value=None,
            coverage="partial",
        )
    selected = annual[0]
    restated, previous = restatement_for(annual, selected)
    return FieldSelection(
        selected.value,
        "latest_annual",
        selected.confidence,
        (selected,),
        restated=restated,
        previous_value=previous,
        coverage="partial",
    )


def select_eps(facts: list[Fact]) -> FieldSelection:
    direct = [fact for fact in facts if fact.unit == "USD/shares"]
    ttm = select_ttm(direct, allow_annual_ytd_bridge=False)
    annual = select_latest_annual(direct)
    if ttm.value is not None and is_current_enough(ttm, annual):
        return FieldSelection(
            ttm.value,
            "ttm",
            ttm.confidence,
            ttm.facts,
            restated=False,
            previous_value=None,
            coverage=ttm.coverage,
            period_start=ttm.period_start,
            period_end=ttm.period_end,
        )
    return annual


def derived_eps(
    net_income: Decimal | None,
    diluted_shares: Decimal | None,
    basic_shares: Decimal | None,
) -> tuple[Decimal | None, str | None]:
    diluted = ratio(net_income, diluted_shares)
    if diluted is not None:
        return diluted, "net_income_diluted_weighted_average"
    basic = ratio(net_income, basic_shares)
    if basic is not None:
        return basic, "net_income_basic_weighted_average"
    return None, None


def annual_series(facts: Any, concepts: tuple[Concept, ...]) -> list[dict[str, Any]]:
    by_year: dict[int, Fact] = {}
    for fact in sorted(dedupe(parse_field_facts(facts, "revenue", concepts)), key=sort_key):
        if fact.is_annual:
            by_year[fact.fy] = fact
    rows = sorted(by_year.values(), key=sort_key, reverse=True)
    return [{"year": row.fy, "revenue": row.value} for row in rows[:5]]


def restatement_for(facts: list[Fact], selected: Fact) -> tuple[bool, Decimal | None]:
    previous_values = [
        fact.value
        for fact in facts
        if fact.period_key == selected.period_key
        and fact.filed < selected.filed
        and fact.value != selected.value
    ]
    if previous_values:
        return True, previous_values[-1]
    return False, None


def with_restatement(selection: FieldSelection, raw_facts: list[Fact]) -> FieldSelection:
    if not selection.facts:
        return selection
    restated, previous = restatement_for(raw_facts, selection.facts[0])
    return FieldSelection(
        selection.value,
        selection.basis,
        selection.confidence,
        selection.facts,
        restated=restated,
        previous_value=previous,
        coverage=selection.coverage,
        period_start=selection.period_start,
        period_end=selection.period_end,
        source_fact_items=selection.source_fact_items,
    )


def best_selection(selections: list[FieldSelection]) -> FieldSelection:
    return sorted(selections, key=selection_key, reverse=True)[0]


def selection_key(selection: FieldSelection) -> tuple[str, int]:
    if not selection.facts:
        return ("", 0)
    period_end = selection.period_end or max(fact.end for fact in selection.facts)
    return (period_end, -selection.facts[0].concept_rank)


def sort_key(fact: Fact) -> tuple[str, str, int, int]:
    return (fact.end, fact.filed, -FORM_RANK[fact.form], -fact.concept_rank)
