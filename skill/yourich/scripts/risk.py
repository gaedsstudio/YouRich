import argparse
from decimal import Decimal

from _core import ToolError, add_input_arg, decimal_or_none, load_financials, write_json
from financial_health import financial_health
from valuation import valuation

MIN_SHARE_PERIODS = 2


def risk_checks(company: dict[str, object]) -> dict[str, object]:
    health = financial_health(company)["metrics"]
    value = valuation(company)["metrics"]
    checks = [
        maximum(
            "debt_risk",
            health["debt_to_equity"]["value"],
            Decimal("1.5"),
            "medium",
            "Debt/equity is above the configured threshold.",
        ),
        minimum(
            "liquidity_risk",
            health["current_ratio"]["value"],
            Decimal("1.0"),
            "medium",
            "Current ratio is below the configured threshold.",
        ),
        minimum(
            "negative_equity",
            company.get("shareholder_equity"),
            Decimal("0"),
            "high",
            "Shareholder equity is negative.",
        ),
        minimum(
            "earnings_deterioration",
            health["earnings_growth"]["value"],
            Decimal("0"),
            "medium",
            "Multi-year earnings growth is negative.",
        ),
        minimum(
            "fcf_deterioration",
            health["fcf_consistency"]["value"],
            Decimal("50"),
            "medium",
            "Free cash flow consistency is below 50%.",
        ),
        minimum(
            "margin_deterioration",
            health["operating_margin"]["value"],
            Decimal("0"),
            "medium",
            "Operating margin is negative.",
        ),
        maximum(
            "valuation_risk",
            value["pe"]["value"],
            Decimal("45"),
            "low",
            "P/E is above the configured threshold.",
        ),
        maximum(
            "share_dilution",
            share_growth(company),
            Decimal("5"),
            "low",
            "Shares outstanding increased by more than 5%.",
        ),
    ]
    return {"ticker": company.get("ticker"), "risk_checks": checks}


def maximum(
    risk_id: str,
    raw_value: object,
    threshold: Decimal,
    severity: str,
    explanation: str,
) -> dict[str, object]:
    value = decimal_or_none(raw_value)
    if value is None:
        return check(risk_id, severity, "unknown", None, threshold, explanation)
    return check(
        risk_id,
        severity,
        "triggered" if value > threshold else "clear",
        value,
        threshold,
        explanation,
    )


def minimum(
    risk_id: str,
    raw_value: object,
    threshold: Decimal,
    severity: str,
    explanation: str,
) -> dict[str, object]:
    value = decimal_or_none(raw_value)
    if value is None:
        return check(risk_id, severity, "unknown", None, threshold, explanation)
    return check(
        risk_id,
        severity,
        "triggered" if value < threshold else "clear",
        value,
        threshold,
        explanation,
    )


def check(
    risk_id: str,
    severity: str,
    status: str,
    value: Decimal | None,
    threshold: Decimal,
    explanation: str,
) -> dict[str, object]:
    return {
        "id": risk_id,
        "severity": severity,
        "status": status,
        "value": value,
        "threshold": threshold,
        "explanation": explanation,
    }


def share_growth(company: dict[str, object]) -> Decimal | None:
    annuals = company.get("annuals")
    values: list[Decimal] = []
    if isinstance(annuals, list):
        for item in annuals:
            if isinstance(item, dict):
                value = decimal_or_none(item.get("shares_outstanding"))
                if value is not None:
                    values.append(value)
    if len(values) < MIN_SHARE_PERIODS or values[-1] == 0:
        return None
    return (values[0] - values[-1]) / values[-1] * Decimal("100")


def main() -> int:
    parser = argparse.ArgumentParser()
    add_input_arg(parser)
    args = parser.parse_args()
    try:
        write_json(risk_checks(load_financials(args)))
    except ToolError as exc:
        write_json({"status": "error", "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
