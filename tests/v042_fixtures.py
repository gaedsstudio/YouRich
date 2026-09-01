from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from _sec_types import Fact

REVENUE_CONCEPT = "RevenueFromContractWithCustomerExcludingAssessedTax"
NET_INCOME_CONCEPT = "NetIncomeLoss"
GROSS_PROFIT_CONCEPT = "GrossProfit"
OPERATING_INCOME_CONCEPT = "OperatingIncomeLoss"
OCF_CONCEPT = "NetCashProvidedByUsedInOperatingActivities"
CAPEX_CONCEPT = "PaymentsToAcquirePropertyPlantAndEquipment"


@dataclass(frozen=True, slots=True)
class FactSpec:
    value: Decimal
    concept: str = REVENUE_CONCEPT
    unit: str = "USD"
    fp: str = "Q3"
    form: str = "10-Q"
    start: str = "2025-09-28"
    end: str = "2026-06-27"
    fy: int = 2026
    filed: str = "2026-08-01"
    accn: str = "accn-current"


def apple_bridge_facts(annual: Decimal, current_ytd: Decimal, prior_ytd: Decimal) -> list[Fact]:
    return [
        fact(
            FactSpec(
                annual,
                fp="FY",
                form="10-K",
                start="2024-09-29",
                end="2025-09-27",
                fy=2025,
                filed="2025-10-31",
                accn="accn-annual",
            )
        ),
        fact(FactSpec(current_ytd)),
        fact(
            FactSpec(
                prior_ytd,
                start="2024-09-29",
                end="2025-06-28",
                fy=2025,
                filed="2025-08-01",
                accn="accn-prior",
            )
        ),
    ]


def additive_bridge_payload() -> dict[str, Any]:
    return {
        "facts": {
            "us-gaap": {
                REVENUE_CONCEPT: {"units": {"USD": rows("416.161", "364.357", "313.695")}},
                GROSS_PROFIT_CONCEPT: {"units": {"USD": rows("200", "170", "150")}},
                OPERATING_INCOME_CONCEPT: {"units": {"USD": rows("140", "120", "100")}},
                NET_INCOME_CONCEPT: {"units": {"USD": rows("110", "94", "80")}},
                OCF_CONCEPT: {"units": {"USD": rows("120", "106", "90")}},
                CAPEX_CONCEPT: {"units": {"USD": rows("12", "11", "9")}},
            },
            "dei": {},
        }
    }


def rows(annual: str, current_ytd: str, prior_ytd: str) -> list[dict[str, Any]]:
    return [
        row(annual, "FY", "10-K", "2024-09-29", "2025-09-27", 2025, "2025-10-31"),
        row(current_ytd, "Q3", "10-Q", "2025-09-28", "2026-06-27", 2026, "2026-08-01"),
        row(prior_ytd, "Q3", "10-Q", "2024-09-29", "2025-06-28", 2025, "2025-08-01"),
    ]


def row(
    value: str,
    fp: str,
    form: str,
    start: str,
    end: str,
    fy: int,
    filed: str,
) -> dict[str, Any]:
    return {
        "val": value,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
        "start": start,
        "end": end,
        "accn": f"accn-{fy}-{fp}-{filed}",
    }


def fact(spec: FactSpec) -> Fact:
    return Fact(
        field="revenue",
        taxonomy="us-gaap",
        concept=spec.concept,
        unit=spec.unit,
        value=spec.value,
        fy=spec.fy,
        fp=spec.fp,
        form=spec.form,
        filed=spec.filed,
        end=spec.end,
        start=spec.start,
        frame=None,
        accn=spec.accn,
        concept_rank=0,
    )
