from __future__ import annotations

from _sec_types import FORM_RANK, Fact, FieldSelection, PeriodClass

COMBINED_DEBT_CONCEPTS = {
    "DebtAndFinanceLeaseObligations",
    "LongTermDebtAndFinanceLeaseObligations",
}
CURRENT_DEBT_CONCEPTS = {
    "ShortTermBorrowings",
    "LongTermDebtCurrent",
    "LongTermDebtAndFinanceLeaseObligationsCurrent",
}
NONCURRENT_DEBT_CONCEPTS = {
    "LongTermDebtNoncurrent",
    "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
}


def select_total_debt(candidates: list[Fact]) -> FieldSelection:
    combined = [fact for fact in candidates if fact.concept in COMBINED_DEBT_CONCEPTS]
    if combined:
        return snapshot_selection(combined)
    current = first_snapshot(candidates, CURRENT_DEBT_CONCEPTS)
    noncurrent = first_snapshot(candidates, NONCURRENT_DEBT_CONCEPTS)
    if current is None or noncurrent is None:
        return FieldSelection(
            None,
            "total_debt_partial",
            "LOW",
            tuple(fact for fact in (current, noncurrent) if fact is not None),
            restated=False,
            previous_value=None,
        )
    selected = composed_fact(current, noncurrent)
    return FieldSelection(
        selected.value,
        "composed_snapshot",
        "HIGH",
        (selected,),
        restated=False,
        previous_value=None,
    )


def snapshot_selection(facts: list[Fact]) -> FieldSelection:
    selected = sorted(facts, key=sort_key, reverse=True)[0]
    return FieldSelection(
        selected.value,
        "latest_snapshot",
        selected.confidence,
        (selected,),
        restated=False,
        previous_value=None,
    )


def first_snapshot(facts: list[Fact], concepts: set[str]) -> Fact | None:
    matches = [
        fact
        for fact in facts
        if fact.concept in concepts and fact.period_class == PeriodClass.INSTANT
    ]
    if not matches:
        return None
    return sorted(matches, key=sort_key, reverse=True)[0]


def composed_fact(current: Fact, noncurrent: Fact) -> Fact:
    selected = sorted([current, noncurrent], key=sort_key, reverse=True)[0]
    return Fact(
        field="total_debt",
        taxonomy=selected.taxonomy,
        concept="ComposedTotalDebt",
        unit=selected.unit,
        value=current.value + noncurrent.value,
        fy=selected.fy,
        fp=selected.fp,
        form=selected.form,
        filed=selected.filed,
        end=selected.end,
        start=None,
        frame=None,
        accn=selected.accn,
        concept_rank=0,
        source_kind="composed_snapshot",
        derived_from=(current.concept, noncurrent.concept),
    )


def sort_key(fact: Fact) -> tuple[str, str, int, int]:
    return (fact.end, fact.filed, -FORM_RANK[fact.form], -fact.concept_rank)
