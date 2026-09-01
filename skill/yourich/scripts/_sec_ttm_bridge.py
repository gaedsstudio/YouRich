from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from _sec_types import Fact, FieldSelection, PeriodClass, duration_days, next_day

FactKey = tuple[str, str, str]
YtdKey = tuple[FactKey, int, str]


@dataclass(frozen=True, slots=True)
class AnnualYtdBridge:
    annual: Fact
    current_ytd: Fact
    prior_ytd: Fact

    @property
    def value(self) -> Decimal:
        return self.annual.value + self.current_ytd.value - self.prior_ytd.value

    @property
    def period_start(self) -> str | None:
        return next_day(self.prior_ytd.end)

    @property
    def period_end(self) -> str:
        return self.current_ytd.end


def select_annual_ytd_ttm(facts: list[Fact]) -> FieldSelection:
    bridges = annual_ytd_bridges(facts)
    if not bridges:
        return FieldSelection(
            None,
            "ttm",
            "LOW",
            (),
            restated=False,
            previous_value=None,
            coverage="partial",
        )
    bridge = sorted(bridges, key=bridge_key, reverse=True)[0]
    return FieldSelection(
        bridge.value,
        "ttm",
        min_confidence((bridge.annual, bridge.current_ytd, bridge.prior_ytd)),
        (bridge.current_ytd, bridge.annual, bridge.prior_ytd),
        restated=False,
        previous_value=None,
        coverage="complete",
        period_start=bridge.period_start,
        period_end=bridge.period_end,
        source_fact_items=(bridge.annual, bridge.prior_ytd, bridge.current_ytd),
    )


def annual_ytd_bridges(facts: list[Fact]) -> list[AnnualYtdBridge]:
    annuals: dict[tuple[FactKey, int], list[Fact]] = {}
    ytds: dict[YtdKey, list[Fact]] = {}
    for fact in facts:
        key = fact_key(fact)
        if fact.period_class == PeriodClass.ANNUAL:
            annuals.setdefault((key, fact.fy), []).append(fact)
        if is_ytd(fact):
            ytds.setdefault((key, fact.fy, fact.fp), []).append(fact)
    bridges: list[AnnualYtdBridge] = []
    for (key, current_fy, fp), current_facts in ytds.items():
        prior_fy = current_fy - 1
        for current in current_facts:
            for annual in annuals.get((key, prior_fy), []):
                for prior in ytds.get((key, prior_fy, fp), []):
                    bridge = AnnualYtdBridge(annual, current, prior)
                    if is_valid_bridge(bridge, facts):
                        bridges.append(bridge)
    return bridges


def fact_key(fact: Fact) -> FactKey:
    return (fact.taxonomy, fact.concept, fact.unit)


def is_valid_bridge(bridge: AnnualYtdBridge, facts: list[Fact]) -> bool:
    annual = bridge.annual
    current = bridge.current_ytd
    prior = bridge.prior_ytd
    return (
        annual.period_class == PeriodClass.ANNUAL
        and is_ytd(current)
        and current.period_class == prior.period_class
        and annual.fy + 1 == current.fy
        and prior.fy == annual.fy
        and prior.fp == current.fp
        and same_concept_unit(annual, current, prior)
        and prior.start == annual.start
        and current.start == next_day(annual.end)
        and bridge.period_start is not None
        and same_duration(current, prior)
        and not any(has_conflicting_restatement(facts, item) for item in (annual, current, prior))
    )


def is_ytd(fact: Fact) -> bool:
    return fact.period_class in {PeriodClass.YTD_6M, PeriodClass.YTD_9M}


def same_concept_unit(annual: Fact, current: Fact, prior: Fact) -> bool:
    return (
        annual.taxonomy == current.taxonomy == prior.taxonomy
        and annual.concept == current.concept == prior.concept
        and annual.unit == current.unit == prior.unit
    )


def same_duration(current: Fact, prior: Fact) -> bool:
    return duration_days(current.start or "", current.end) == duration_days(
        prior.start or "", prior.end
    )


def has_conflicting_restatement(facts: list[Fact], selected: Fact) -> bool:
    return any(
        fact.period_key == selected.period_key
        and fact.filed != selected.filed
        and fact.value != selected.value
        for fact in facts
    )


def bridge_key(bridge: AnnualYtdBridge) -> tuple[str, str, int]:
    return (bridge.current_ytd.end, bridge.current_ytd.filed, -bridge.current_ytd.concept_rank)


def min_confidence(facts: tuple[Fact, ...]) -> str:
    values = {fact.confidence for fact in facts}
    if "LOW" in values:
        return "LOW"
    if "MEDIUM" in values:
        return "MEDIUM"
    return "HIGH"
