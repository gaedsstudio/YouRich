from __future__ import annotations

from typing import Any, Final

SIC_INDUSTRIES: Final = {
    "3674": ("Technology", "Semiconductors", "Semiconductors"),
    "3571": ("Technology", "Hardware", "Computing Devices"),
    "7372": ("Technology", "Software", "Software"),
    "5331": ("Consumer Staples", "Retail", "Discount Retail"),
    "5411": ("Consumer Staples", "Retail", "Food Retail"),
    "2086": ("Consumer Staples", "Beverages", "Nonalcoholic Beverages"),
}
TICKER_INDUSTRIES: Final = {
    "NVDA": ("Technology", "Semiconductors", "Accelerated Computing"),
    "AMD": ("Technology", "Semiconductors", "Processors And Accelerators"),
    "AVGO": ("Technology", "Semiconductors", "Infrastructure Semiconductors"),
    "INTC": ("Technology", "Semiconductors", "Processors And Foundry"),
    "AAPL": ("Technology", "Consumer Hardware", "Devices And Services"),
    "MSFT": ("Technology", "Software", "Cloud And Productivity"),
    "GOOGL": ("Communication Services", "Internet Platforms", "Search And Advertising"),
    "WMT": ("Consumer Staples", "Retail", "Discount Retail"),
    "COST": ("Consumer Staples", "Retail", "Warehouse Retail"),
    "TGT": ("Consumer Discretionary", "Retail", "General Merchandise"),
    "KO": ("Consumer Staples", "Beverages", "Nonalcoholic Beverages"),
    "PEP": ("Consumer Staples", "Beverages", "Snacks And Beverages"),
}


def classify_industry(company: dict[str, Any]) -> dict[str, Any]:
    sic = str(company.get("sic") or "")
    ticker = str(company.get("ticker") or "").upper()
    mapped = SIC_INDUSTRIES.get(sic) or TICKER_INDUSTRIES.get(ticker)
    description = str(company.get("business_description") or "")
    segments = company.get("segments")
    sector, industry, subindustry = mapped or ("Unknown", "Unknown", "Unknown")
    evidence = classification_evidence(company, sic, description, segments, ticker)
    confidence = classification_confidence(
        sic in SIC_INDUSTRIES, ticker in TICKER_INDUSTRIES, description, segments
    )
    warnings = [] if confidence == "HIGH" else ["INDUSTRY_CLASSIFICATION_WEAK"]
    return {
        "sector": sector,
        "industry": industry,
        "subindustry": subindustry,
        "sic": sic or None,
        "confidence": confidence,
        "evidence": evidence,
        "warnings": warnings,
    }


def classification_evidence(
    company: dict[str, Any], sic: str, description: str, segments: Any, ticker: str
) -> list[dict[str, str]]:
    evidence = []
    if sic:
        evidence.append({"source": "SEC:SIC", "excerpt": sic})
    if not sic and ticker in TICKER_INDUSTRIES:
        evidence.append({"source": "curated_peer_universe", "excerpt": ticker})
    if description:
        evidence.append(
            {
                "source": str(
                    company.get("field_sources", {}).get("business_description") or "company"
                ),
                "excerpt": description[:220],
            }
        )
    if isinstance(segments, list) and segments:
        names = [str(item.get("name")) for item in segments if isinstance(item, dict)]
        evidence.append({"source": "reported_segments", "excerpt": ", ".join(names[:4])})
    return evidence


def classification_confidence(
    has_sic: bool, has_ticker_default: bool, description: str, segments: Any
) -> str:
    has_segments = isinstance(segments, list) and bool(segments)
    if has_sic and description and has_segments:
        return "HIGH"
    if has_sic or has_ticker_default:
        return "MEDIUM"
    return "LOW"
