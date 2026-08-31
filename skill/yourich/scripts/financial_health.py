import argparse
from decimal import Decimal

from _core import (
    ToolError,
    add_input_arg,
    decimal_or_none,
    load_financials,
    metric,
    percent,
    ratio,
    write_json,
)

MIN_GROWTH_PERIODS = 2


def financial_health(company: dict[str, object]) -> dict[str, object]:
    current_assets = decimal_or_none(company.get("current_assets"))
    current_liabilities = decimal_or_none(company.get("current_liabilities"))
    inventory = decimal_or_none(company.get("inventory")) or Decimal("0")
    total_debt = decimal_or_none(company.get("total_debt"))
    total_assets = decimal_or_none(company.get("total_assets"))
    equity = decimal_or_none(company.get("shareholder_equity"))
    revenue = decimal_or_none(company.get("revenue"))
    gross_profit = decimal_or_none(company.get("gross_profit"))
    operating_income = decimal_or_none(company.get("operating_income"))
    net_income = decimal_or_none(company.get("net_income"))
    fcf = decimal_or_none(company.get("free_cash_flow"))
    invested = None if total_debt is None or equity is None else total_debt + equity
    metrics = {
        "current_ratio": metric(
            ratio(current_assets, current_liabilities),
            "current assets / current liabilities",
            {
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
            },
        ),
        "quick_ratio": metric(
            ratio(
                None if current_assets is None else current_assets - inventory,
                current_liabilities,
            ),
            "(current assets - inventory) / current liabilities",
            {
                "current_assets": current_assets,
                "inventory": inventory,
                "current_liabilities": current_liabilities,
            },
        ),
        "debt_to_equity": metric(
            ratio(total_debt, equity),
            "total debt / shareholder equity",
            {"total_debt": total_debt, "shareholder_equity": equity},
        ),
        "debt_to_assets": metric(
            ratio(total_debt, total_assets),
            "total debt / total assets",
            {"total_debt": total_debt, "total_assets": total_assets},
        ),
        "roe": metric(
            percent(net_income, equity),
            "net income / shareholder equity * 100",
            {"net_income": net_income, "shareholder_equity": equity},
        ),
        "roa": metric(
            percent(net_income, total_assets),
            "net income / total assets * 100",
            {"net_income": net_income, "total_assets": total_assets},
        ),
        "roic": metric(
            percent(operating_income, invested),
            "operating income / invested capital * 100",
            {"operating_income": operating_income, "invested_capital": invested},
        ),
        "gross_margin": metric(
            percent(gross_profit, revenue),
            "gross profit / revenue * 100",
            {"gross_profit": gross_profit, "revenue": revenue},
        ),
        "operating_margin": metric(
            percent(operating_income, revenue),
            "operating income / revenue * 100",
            {"operating_income": operating_income, "revenue": revenue},
        ),
        "net_margin": metric(
            percent(net_income, revenue),
            "net income / revenue * 100",
            {"net_income": net_income, "revenue": revenue},
        ),
        "fcf_margin": metric(
            percent(fcf, revenue),
            "free cash flow / revenue * 100",
            {"free_cash_flow": fcf, "revenue": revenue},
        ),
        "revenue_growth": metric(
            growth(company, "revenue"),
            "latest annual revenue / oldest annual revenue - 1",
            {},
        ),
        "earnings_growth": metric(
            growth(company, "net_income"),
            "latest annual earnings / oldest annual earnings - 1",
            {},
        ),
        "earnings_consistency": metric(
            positive_rate(company, "net_income"),
            "positive net income years / available years * 100",
            {},
        ),
        "fcf_consistency": metric(
            positive_rate(company, "free_cash_flow"),
            "positive FCF years / available years * 100",
            {},
        ),
    }
    return {"ticker": company.get("ticker"), "metrics": metrics}


def growth(company: dict[str, object], field: str) -> Decimal | None:
    values = annual_field_values(company, field)
    if len(values) < MIN_GROWTH_PERIODS or values[-1] == 0:
        return None
    return (values[0] - values[-1]) / values[-1] * Decimal("100")


def positive_rate(company: dict[str, object], field: str) -> Decimal | None:
    values = annual_field_values(company, field)
    if not values:
        return None
    return Decimal(sum(1 for value in values if value > 0)) / Decimal(len(values)) * Decimal("100")


def annual_field_values(company: dict[str, object], field: str) -> list[Decimal]:
    annuals = company.get("annuals")
    values: list[Decimal] = []
    if isinstance(annuals, list):
        for item in annuals:
            if isinstance(item, dict):
                value = decimal_or_none(item.get(field))
                if value is not None:
                    values.append(value)
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    add_input_arg(parser)
    args = parser.parse_args()
    try:
        write_json(financial_health(load_financials(args)))
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
