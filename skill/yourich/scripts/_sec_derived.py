from __future__ import annotations

from decimal import Decimal
from typing import Any

from _core import ratio
from _sec_facts import derived_eps
from _sec_types import FieldSelection, source_fact, source_fact_key


def apply_derived_values(fields: dict[str, Any], selections: dict[str, Any]) -> None:
    fcf_basis = free_cash_flow_basis(selections)
    fields["free_cash_flow"] = free_cash_flow(fields) if fcf_basis != "unavailable" else None
    if fields["free_cash_flow"] is not None:
        fields["field_sources"]["free_cash_flow"] = (
            "computed: operating_cash_flow - abs(capital_expenditures)"
        )
        fields["fact_metadata"]["free_cash_flow"] = duration_derived_metadata(
            fcf_basis,
            ("operating_cash_flow", "capital_expenditures"),
            selections,
        )
    fields["book_value_per_share"] = ratio(
        fields["shareholder_equity"], fields["shares_outstanding"]
    )
    if fields["book_value_per_share"] is not None:
        fields["field_sources"]["book_value_per_share"] = (
            "computed: latest_shareholder_equity / latest_shares_outstanding"
        )
    if fields.get("eps") is None:
        eps, method = derived_eps(
            fields.get("net_income"),
            fields.get("weighted_average_diluted_shares"),
            fields.get("weighted_average_basic_shares"),
        )
        fields["eps"] = eps
        if eps is not None:
            fields["field_sources"]["eps"] = "computed: net_income / weighted_average_shares"
            fields["fact_metadata"]["eps"] = derived_metadata(
                method or "derived_eps", ("net_income",)
            )
    fields["eps_method"] = eps_method(fields, selections)


def free_cash_flow(fields: dict[str, Any]) -> Decimal | None:
    operating = fields.get("operating_cash_flow")
    capex = fields.get("capital_expenditures")
    if not isinstance(operating, Decimal) or not isinstance(capex, Decimal):
        return None
    return operating - abs(capex)


def remember_financial_period(company: dict[str, Any], metadata: dict[str, Any]) -> None:
    filed = metadata.get("filed")
    period = metadata.get("fp")
    period_end = metadata.get("period_end")
    current_filed = company["data_freshness"].get("latest_financial_filed")
    if isinstance(filed, str) and (not isinstance(current_filed, str) or filed > current_filed):
        company["data_freshness"]["latest_financial_filed"] = filed
        company["data_freshness"]["latest_financial_period"] = period
        company["data_freshness"]["latest_financial_period_end"] = period_end


def derived_metadata(basis: str, fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        "basis": basis,
        "type": "derived_metric",
        "derived_from": list(fields),
        "coverage": "complete" if basis == "ttm" else "partial",
        "confidence": "HIGH",
    }


def duration_derived_metadata(
    basis: str, fields: tuple[str, str], selections: dict[str, Any]
) -> dict[str, Any]:
    components = [
        selection
        for field in fields
        if isinstance(selection := selections.get(field), FieldSelection)
    ]
    metadata = derived_metadata(basis, fields)
    metadata["period_start"] = common_selection_start(components)
    metadata["period_end"] = common_selection_end(components)
    metadata["component_periods"] = [
        f"{field}:{selection_start(selection)}:{selection_end(selection)}"
        for field in fields
        if isinstance(selection := selections.get(field), FieldSelection)
    ]
    metadata["source_facts"] = [
        source_fact(fact)
        for selection in components
        for fact in sorted(selection.source_fact_items or selection.facts, key=source_fact_key)
    ]
    return metadata


def common_selection_start(selections: list[FieldSelection]) -> str | None:
    starts = {selection_start(selection) for selection in selections}
    return starts.pop() if len(starts) == 1 else None


def common_selection_end(selections: list[FieldSelection]) -> str | None:
    ends = {selection_end(selection) for selection in selections}
    return ends.pop() if len(ends) == 1 else None


def selection_start(selection: FieldSelection) -> str | None:
    if selection.period_start is not None:
        return selection.period_start
    return min((fact.start for fact in selection.facts if fact.start is not None), default=None)


def selection_end(selection: FieldSelection) -> str | None:
    if selection.period_end is not None:
        return selection.period_end
    return max((fact.end for fact in selection.facts), default=None)


def free_cash_flow_basis(selections: dict[str, Any]) -> str:
    operating = selections.get("operating_cash_flow")
    capex = selections.get("capital_expenditures")
    if operating is None or capex is None:
        return "unavailable"
    if operating.basis == "ttm" and capex.basis == "ttm":
        return "ttm"
    if operating.basis == "latest_annual" and capex.basis == "latest_annual":
        return "latest_annual"
    return "unavailable"


def eps_method(fields: dict[str, Any], selections: dict[str, Any]) -> str | None:
    if fields.get("eps") is None:
        return None
    metadata = fields.get("fact_metadata", {}).get("eps")
    if isinstance(metadata, dict):
        if metadata.get("basis") == "ttm" and metadata.get("concept") == "EarningsPerShareDiluted":
            return "diluted_ttm"
        return str(metadata.get("basis"))
    selection = selections.get("eps")
    if selection is not None:
        return str(selection.basis)
    return None
