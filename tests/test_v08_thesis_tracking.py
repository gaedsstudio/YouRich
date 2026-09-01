import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skill" / "yourich" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _report_format import render_markdown  # noqa: E402
from _report_model import build_report  # noqa: E402
from _research_diff import compare_snapshots  # noqa: E402
from _research_snapshot import snapshot_fingerprint, snapshot_identity  # noqa: E402
from _research_store import ResearchStore, load_snapshot_file  # noqa: E402
from _thesis_tracker import build_thesis  # noqa: E402
from _tracking_report import render_tracking_markdown  # noqa: E402
from v08_fixtures import change_for, company, run_cli, snapshot  # noqa: E402


def test_first_baseline_creation_when_no_previous_snapshot(tmp_path: Path) -> None:
    current = snapshot("NVDA")
    store = ResearchStore(tmp_path)

    result = store.capture(current)

    assert result["status"] == "BASELINE_CREATED"
    assert result["previous_snapshot"] is None
    assert result["current_snapshot"]["id"] == snapshot_identity(current)["id"]
    assert "NO_PREVIOUS_SNAPSHOT" in result["warnings"]


def test_snapshot_write_read_and_atomic_write(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    result = store.capture(snapshot("AAPL"))

    stored = load_snapshot_file(Path(result["current_snapshot"]["path"]))

    assert stored["ticker"] == "AAPL"
    assert stored["schema_version"] == "research_snapshot.v1"
    assert list(tmp_path.rglob("*.tmp")) == []


def test_snapshot_fingerprint_excludes_volatile_fields() -> None:
    first = snapshot("AMD", created_at="2026-09-01T00:00:00Z")
    second = snapshot("AMD", created_at="2026-09-02T00:00:00Z")
    second["financials"]["market_quote"] = {"retrieved_at": "2026-09-02T00:00:00Z"}

    assert snapshot_fingerprint(first) == snapshot_fingerprint(second)


def test_duplicate_suppression_when_content_is_identical(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    first = store.capture(snapshot("WMT", created_at="2026-09-01T00:00:00Z"))
    second = store.capture(snapshot("WMT", created_at="2026-09-02T00:00:00Z"))

    assert first["status"] == "BASELINE_CREATED"
    assert second["status"] == "NO_MATERIAL_CHANGE"
    assert len(store.list("WMT")) == 1


def test_latest_snapshot_selection_and_history_ordering(tmp_path: Path) -> None:
    store = ResearchStore(tmp_path)
    store.save(snapshot("NVDA", created_at="2026-09-01T00:00:00Z"))
    latest = store.save(snapshot("NVDA", created_at="2026-10-15T00:00:00Z", revenue="1300"))

    stored_latest = store.latest("NVDA")
    assert stored_latest is not None
    assert stored_latest["id"] == latest["id"]
    assert [item["created_at"] for item in store.history("NVDA")] == [
        "2026-09-01T00:00:00Z",
        "2026-10-15T00:00:00Z",
    ]


def test_financial_diff_and_basis_change_handling() -> None:
    result = compare_snapshots(
        snapshot("NVDA", revenue="1000", revenue_growth="10", basis="latest_annual"),
        snapshot("NVDA", revenue="1160", revenue_growth="16", basis="ttm"),
    )

    revenue = change_for(result, "FINANCIAL", "revenue")
    growth = change_for(result, "FINANCIAL", "revenue_growth")
    assert revenue["direction"] == "NOT_COMPARABLE"
    assert revenue["materiality"] == "MATERIAL"
    assert "SNAPSHOT_BASIS_CHANGED" in result["warnings"]
    assert growth["direction"] == "IMPROVED"


def test_earnings_and_guidance_diff() -> None:
    result = compare_snapshots(
        snapshot("NVDA", earnings_period="Q1 FY2026", guidance_status="REITERATED"),
        snapshot("NVDA", earnings_period="Q2 FY2026", guidance_status="RAISED"),
    )

    earnings = change_for(result, "EARNINGS", "latest_earnings_period")
    guidance = change_for(result, "GUIDANCE", "guidance_direction")
    assert earnings["direction"] == "NEW"
    assert guidance["direction"] == "IMPROVED"


def test_valuation_required_growth_deterioration() -> None:
    result = compare_snapshots(
        snapshot("NVDA", pe="32", fcf_yield="3.2", required_fcf_cagr="18.2"),
        snapshot("NVDA", pe="45", fcf_yield="2.5", required_fcf_cagr="22.7"),
    )

    growth = change_for(result, "VALUATION", "required_fcf_cagr")
    pe = change_for(result, "VALUATION", "pe")
    assert growth["direction"] == "WORSENED"
    assert growth["materiality"] == "MATERIAL"
    assert pe["direction"] == "WORSENED"


def test_risk_newly_triggered_and_resolved() -> None:
    previous = snapshot("AMD", risks={"debt_risk": "clear", "valuation_risk": "triggered"})
    current = snapshot("AMD", risks={"debt_risk": "triggered", "valuation_risk": "clear"})

    result = compare_snapshots(previous, current)

    assert change_for(result, "RISK", "debt_risk")["direction"] == "NEW"
    assert change_for(result, "RISK", "valuation_risk")["direction"] == "REMOVED"


def test_peer_set_change_is_not_compared_as_identical_universe() -> None:
    previous = snapshot("NVDA", peers=["AMD", "AVGO"])
    current = snapshot("NVDA", peers=["AMD", "INTC"])

    result = compare_snapshots(previous, current)

    assert change_for(result, "PEERS", "peer_set")["direction"] == "NOT_COMPARABLE"
    assert "PEER_SET_CHANGED" in result["warnings"]


def test_thesis_strengthened_weakened_and_mixed() -> None:
    strengthened = compare_snapshots(
        snapshot("NVDA", revenue_growth="10", net_margin="20"),
        snapshot("NVDA", revenue_growth="18", net_margin="26"),
    )
    weakened = compare_snapshots(
        snapshot("AAPL", revenue_growth="18", net_margin="26"),
        snapshot("AAPL", revenue_growth="10", net_margin="20"),
    )
    mixed = compare_snapshots(
        snapshot("AMD", revenue_growth="10", net_margin="20", pe="30"),
        snapshot("AMD", revenue_growth="18", net_margin="20", pe="45"),
    )

    assert strengthened["thesis_change"]["overall_change"] == "STRENGTHENED"
    assert weakened["thesis_change"]["overall_change"] == "WEAKENED"
    assert mixed["thesis_change"]["overall_change"] == "MIXED"


def test_thesis_vs_valuation_separation() -> None:
    result = compare_snapshots(
        snapshot("NVDA", revenue_growth="10", net_margin="20", pe="30"),
        snapshot("NVDA", revenue_growth="18", net_margin="26", pe="45"),
    )

    assert result["thesis_change"]["dimensions"]["growth_outlook"] == "IMPROVED"
    assert result["valuation_change"]["direction"] == "WORSENED"


def test_watch_variables_and_thesis_risk_conditions() -> None:
    thesis = build_thesis(snapshot("NVDA", fcf_margin="41", required_fcf_cagr="22"))

    variables = {item["name"]: item for item in thesis["watch_variables"]}
    conditions = {item["type"] for item in thesis["thesis_risk_conditions"]}
    assert variables["FCF margin"]["negative_trigger"] == "< 35.0%"
    assert variables["Required FCF CAGR"]["watch_reason"]
    assert conditions == {"THESIS_RISK_CONDITION"}
    assert all("SELL_TRIGGER" not in json.dumps(item) for item in thesis["thesis_risk_conditions"])


def test_invalid_and_partial_old_schema_are_reported(tmp_path: Path) -> None:
    ticker_dir = tmp_path / "NVDA"
    ticker_dir.mkdir()
    (ticker_dir / "bad.json").write_text("{bad", encoding="utf-8")
    (ticker_dir / "2026-09-01T000000Z.json").write_text(
        json.dumps({"ticker": "NVDA", "created_at": "2026-09-01T00:00:00Z"}),
        encoding="utf-8",
    )

    history = ResearchStore(tmp_path).history("NVDA")

    assert history[0]["status"] == "SNAPSHOT_SCHEMA_PARTIAL"
    assert history[0]["warnings"] == ["SNAPSHOT_SCHEMA_PARTIAL"]


def test_korean_and_english_tracking_reports() -> None:
    result = compare_snapshots(
        snapshot("NVDA", revenue_growth="10", guidance_status="REITERATED"),
        snapshot("NVDA", revenue_growth="16", guidance_status="RAISED", pe="45"),
    )

    korean = render_tracking_markdown(result, language="ko")
    english = render_tracking_markdown(result, language="en")

    assert "지난 분석 이후" in korean
    assert "계속 볼 항목" in korean
    assert "Since Previous Analysis" in english
    assert "Watch Variables" in english


def test_no_previous_snapshot_does_not_assume_conversation_memory(tmp_path: Path) -> None:
    result = ResearchStore(tmp_path).compare_or_capture_baseline(snapshot("NVDA"))

    assert result["status"] == "BASELINE_CREATED"
    assert result["previous_snapshot"] is None
    assert result["changes"] == []
    assert "NO_PREVIOUS_SNAPSHOT" in result["warnings"]


def test_report_integration_only_when_tracking_context_exists() -> None:
    company_payload = company()
    plain = render_markdown(build_report(company_payload))
    tracked = render_markdown(
        build_report(
            company_payload,
            tracking_context=compare_snapshots(snapshot("AAPL"), snapshot("AAPL", revenue="1200")),
            language="ko",
        )
    )

    assert "지난 분석 이후 변화" not in plain
    assert "지난 분석 이후 변화" in tracked


def test_cli_capture_compare_history_and_latest(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps(company()), encoding="utf-8")
    changed = company()
    changed["revenue"] = "1200"
    second.write_text(json.dumps(changed), encoding="utf-8")

    capture = run_cli(tmp_path, "AAPL", "capture", "--input", str(first), "--format", "json")
    compare = run_cli(tmp_path, "AAPL", "compare", "--input", str(second), "--format", "json")
    against = run_cli(
        tmp_path,
        "AAPL",
        "compare",
        "--input",
        str(second),
        "--against",
        str(capture["current_snapshot"]["id"]),
        "--format",
        "json",
    )
    history = run_cli(tmp_path, "AAPL", "history", "--format", "json")
    latest = run_cli(tmp_path, "AAPL", "latest", "--format", "json")

    assert capture["status"] == "BASELINE_CREATED"
    assert compare["status"] == "CHANGED"
    assert against["status"] == "CHANGED"
    assert len(history["snapshots"]) == 3
    assert latest["snapshot"]["ticker"] == "AAPL"
