import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))


def run_event_cli(tmp_path: Path, payload: dict[str, Any], *args: str) -> dict[str, Any]:
    return json.loads(run_event_cli_text(tmp_path, payload, *args))


def run_event_cli_text(tmp_path: Path, payload: dict[str, Any], *args: str) -> str:
    source = tmp_path / "events.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "event_intelligence.py"), *args, "--input", str(source)],
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    return completed.stdout


def company(ticker: str = "NVDA") -> dict[str, Any]:
    return {
        "ticker": ticker,
        "company": f"{ticker} Corporation",
        "market_cap": "3000000000000",
        "revenue": "120000000000",
        "net_income": "60000000000",
        "total_assets": "200000000000",
        "capital_expenditures": "5000000000",
    }


def filing(
    text: str,
    *,
    accession: str = "0001",
    filing_date: str = "2026-08-20",
    form: str = "8-K",
    item: str = "Item 8.01",
) -> dict[str, Any]:
    return {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "form": form,
        "filing_date": filing_date,
        "period_end": filing_date,
        "accession_number": accession,
        "primary_document": "form8k.htm",
        "filing_url": f"https://www.sec.gov/Archives/{accession}",
        "source": "SEC",
        "items": [item],
        "text": text,
    }


def event_input(
    *filings: dict[str, Any],
    earnings_context: dict[str, Any] | None = None,
    snapshot: dict[str, Any] | None = None,
    official_events: list[dict[str, Any]] | None = None,
    peer_events: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return {
        "company": company(),
        "filings": list(filings),
        "earnings_context": earnings_context,
        "snapshot": snapshot,
        "official_events": official_events or [],
        "peer_events": peer_events or {},
    }


def earnings_context(status: str = "RAISED") -> dict[str, Any]:
    return {
        "latest_earnings": {
            "period": "Q2 FY2026",
            "accession": "earnings-0001",
            "source_url": "https://investor.example/current",
            "published_at": "2026-08-20",
        },
        "guidance_changes": [{"metric": "revenue", "status": status, "period": "FY2026"}],
        "evidence": [{"source": "earnings_release", "excerpt": "Revenue guidance was raised."}],
    }


def baseline(created_at: str = "2026-08-15T00:00:00Z") -> dict[str, Any]:
    return {"created_at": created_at, "ticker": "NVDA"}
