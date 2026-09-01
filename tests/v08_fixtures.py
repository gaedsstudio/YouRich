import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _research_snapshot import build_snapshot  # noqa: E402


def change_for(result: dict[str, Any], category: str, field: str) -> dict[str, Any]:
    return next(
        item
        for item in result["changes"]
        if item["category"] == category and item["field"] == field
    )


def run_cli(tmp_path: Path, *args: str) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_DIR / "thesis_tracker.py"),
            *args,
            "--store-dir",
            str(tmp_path / "store"),
        ],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def snapshot(
    ticker: str,
    *,
    created_at: str = "2026-09-01T00:00:00Z",
    revenue: str = "1000",
    revenue_growth: str = "10",
    net_income: str = "200",
    eps: str = "2",
    operating_margin: str = "25",
    net_margin: str = "20",
    fcf_margin: str = "15",
    pe: str = "30",
    fcf_yield: str = "3.5",
    required_fcf_cagr: str = "18",
    basis: str = "latest_annual",
    earnings_period: str = "Q1 FY2026",
    guidance_status: str = "REITERATED",
    risks: dict[str, str] | None = None,
    peers: list[str] | None = None,
) -> dict[str, Any]:
    return build_snapshot(
        company(
            ticker,
            revenue=revenue,
            revenue_growth=revenue_growth,
            net_income=net_income,
            eps=eps,
            operating_margin=operating_margin,
            net_margin=net_margin,
            fcf_margin=fcf_margin,
            pe=pe,
            fcf_yield=fcf_yield,
            basis=basis,
        ),
        earnings_context=earnings(earnings_period, guidance_status),
        valuation_intelligence=valuation_intelligence(required_fcf_cagr),
        risk_context=risk_context(risks or {"debt_risk": "clear"}),
        peer_context=peer_context(peers or ["AMD", "AVGO"]),
        created_at=created_at,
    )


def company(
    ticker: str = "AAPL",
    *,
    revenue: str = "1000",
    revenue_growth: str = "10",
    net_income: str = "200",
    eps: str = "2",
    operating_margin: str = "25",
    net_margin: str = "20",
    fcf_margin: str = "15",
    pe: str = "30",
    fcf_yield: str = "3.5",
    basis: str = "latest_annual",
) -> dict[str, Any]:
    return {
        "company": f"{ticker} Corporation",
        "ticker": ticker,
        "current_price": "100",
        "market_cap": "10000",
        "shares_outstanding": "100",
        "revenue": revenue,
        "revenue_growth": revenue_growth,
        "gross_profit": "500",
        "operating_income": "250",
        "net_income": net_income,
        "eps": eps,
        "free_cash_flow": "150",
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "fcf_margin": fcf_margin,
        "current_assets": "900",
        "current_liabilities": "450",
        "inventory": "100",
        "total_assets": "1600",
        "total_liabilities": "500",
        "total_debt": "200",
        "shareholder_equity": "800",
        "book_value_per_share": "8",
        "field_sources": {},
        "market_quote": {"timestamp": "2026-08-28", "provider": "test"},
        "data_quality": {},
        "fact_metadata": {
            "revenue": {"basis": basis},
            "net_income": {"basis": basis},
            "eps": {"basis": basis},
            "operating_margin": {"basis": basis},
            "net_margin": {"basis": basis},
            "fcf_margin": {"basis": basis},
        },
        "annuals": [{"revenue": revenue}, {"revenue": "900"}],
        "valuation_history": [],
        "provided_metrics": {"pe": pe, "fcf_yield": fcf_yield},
    }


def earnings(period: str, guidance_status: str) -> dict[str, Any]:
    return {
        "latest_earnings": {"period": period, "accession": f"{period}-ACCESSION"},
        "guidance_changes": [{"metric": "revenue", "status": guidance_status}],
        "thesis_change": {"status": "SLIGHTLY_STRENGTHENED"},
        "changes": [{"change_type": "revenue_acceleration", "status": "IMPROVED"}],
        "evidence": [{"source": "earnings_release", "period": period}],
    }


def valuation_intelligence(required_fcf_cagr: str) -> dict[str, Any]:
    return {
        "reverse_dcf": {"status": "SOLVED", "required_fcf_cagr": required_fcf_cagr},
        "margin_of_safety": {"position": "MATERIAL_DOWNSIDE"},
        "current_valuation": {"metrics": {}},
        "warnings": [],
    }


def risk_context(risks: dict[str, str]) -> dict[str, Any]:
    return {
        "risk_checks": [
            {"id": key, "status": value, "severity": "medium", "explanation": key}
            for key, value in risks.items()
        ]
    }


def peer_context(peers: list[str]) -> dict[str, Any]:
    return {
        "peer_set": {"candidates": [{"ticker": ticker} for ticker in peers]},
        "relative_valuation": [{"metric": "pe", "peer_median": "32", "premium_percent": "20"}],
        "premium_justification": {"status": "PREMIUM_PARTIALLY_SUPPORTED"},
    }
