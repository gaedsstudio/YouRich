from __future__ import annotations

from typing import TYPE_CHECKING, Any

from _sec_facts import parse_field_facts, select_field

if TYPE_CHECKING:
    from _sec_types import Concept, Fact, FieldSelection


def debug_trace(facts: Any, field: str, concepts: tuple[Concept, ...]) -> dict[str, Any]:
    candidates = parse_field_facts(facts, field, concepts)
    selected = select_field(facts, field, concepts)
    selected_key = selected.facts[0].period_key if selected.facts else None
    rejected = []
    for fact in candidates:
        if fact.period_key == selected_key:
            continue
        rejected.append(
            {
                "concept": fact.concept,
                "form": fact.form,
                "filed": fact.filed,
                "period_end": fact.end,
                "reason": rejection_reason(fact, selected),
            }
        )
    return {"selected": selected.metadata(), "rejected": rejected}


def rejection_reason(fact: Fact, selected: FieldSelection) -> str:
    if not selected.facts:
        return "insufficient valid reporting period"
    chosen = selected.facts[0]
    if fact.concept_rank > chosen.concept_rank:
        return "lower concept priority"
    if fact.end < chosen.end:
        return "older period"
    if fact.filed < chosen.filed:
        return "older filing"
    return "not selected by period and form priority"
