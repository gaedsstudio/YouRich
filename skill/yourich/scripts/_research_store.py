from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _core import to_jsonable
from _research_diff import compare_snapshots
from _research_snapshot import snapshot_fingerprint, snapshot_identity


class SnapshotReadError(Exception):
    pass


class ResearchStore:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path.home() / ".yourich" / "research"

    def save(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        identity = snapshot_identity(snapshot)
        enriched = dict(snapshot)
        enriched["id"] = identity["id"]
        enriched["fingerprint"] = snapshot_fingerprint(enriched)
        ticker_dir = self.ticker_dir(str(enriched["ticker"]))
        ticker_dir.mkdir(parents=True, exist_ok=True)
        path = unique_path(ticker_dir / f"{identity['id']}.json")
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(to_jsonable(enriched), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(path)
        return {**identity, "fingerprint": enriched["fingerprint"], "path": str(path)}

    def capture(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        previous = self.latest(str(snapshot.get("ticker") or ""))
        if previous is None:
            current_ref = self.save(snapshot)
            return baseline_result(snapshot, current_ref)
        if previous.get("fingerprint") == snapshot_fingerprint(snapshot):
            return no_material_change_result(previous)
        current_ref = self.save(snapshot)
        current = dict(snapshot)
        current.update(current_ref)
        return compare_snapshots(previous, current)

    def compare_or_capture_baseline(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return self.capture(snapshot)

    def list(self, ticker: str) -> list[dict[str, Any]]:
        return self.history(ticker)

    def history(self, ticker: str) -> list[dict[str, Any]]:
        rows = []
        for path in sorted(self.ticker_dir(ticker).glob("*.json")):
            try:
                rows.append(load_snapshot_file(path))
            except SnapshotReadError:
                continue
        return sorted(rows, key=lambda item: str(item.get("created_at") or ""))

    def latest(self, ticker: str) -> dict[str, Any] | None:
        rows = self.history(ticker)
        return rows[-1] if rows else None

    def by_id(self, ticker: str, snapshot_id: str) -> dict[str, Any] | None:
        path = self.ticker_dir(ticker) / f"{snapshot_id}.json"
        if not path.exists():
            return None
        try:
            return load_snapshot_file(path)
        except SnapshotReadError:
            return None

    def ticker_dir(self, ticker: str) -> Path:
        return self.root / safe_ticker(ticker)


def load_snapshot_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotReadError from exc
    if not isinstance(payload, dict):
        raise SnapshotReadError
    if payload.get("schema_version") != "research_snapshot.v1":
        return {
            **payload,
            "status": "SNAPSHOT_SCHEMA_PARTIAL",
            "warnings": ["SNAPSHOT_SCHEMA_PARTIAL"],
            "path": str(path),
            "id": path.stem,
        }
    return {**payload, "path": str(path), "id": str(payload.get("id") or path.stem)}


def baseline_result(snapshot: dict[str, Any], current_ref: dict[str, Any]) -> dict[str, Any]:
    current = dict(snapshot)
    current.update(current_ref)
    return {
        "ticker": snapshot.get("ticker"),
        "status": "BASELINE_CREATED",
        "previous_snapshot": None,
        "current_snapshot": current_ref,
        "changes": [],
        "thesis_change": {"overall_change": "INSUFFICIENT_EVIDENCE", "dimensions": {}},
        "valuation_change": {"direction": "UNCHANGED"},
        "risk_change": {"direction": "UNCHANGED"},
        "watch_variables": snapshot.get("thesis", {}).get("watch_variables", []),
        "thesis_risk_conditions": snapshot.get("thesis", {}).get("thesis_risk_conditions", []),
        "warnings": ["NO_PREVIOUS_SNAPSHOT"],
        "data_quality": snapshot.get("data_quality", {}),
    }


def no_material_change_result(previous: dict[str, Any]) -> dict[str, Any]:
    ref = {
        "id": previous.get("id"),
        "created_at": previous.get("created_at"),
        "fingerprint": previous.get("fingerprint"),
        "path": previous.get("path"),
    }
    return {
        "ticker": previous.get("ticker"),
        "status": "NO_MATERIAL_CHANGE",
        "previous_snapshot": ref,
        "current_snapshot": ref,
        "changes": [],
        "thesis_change": {"overall_change": "UNCHANGED", "dimensions": {}},
        "valuation_change": {"direction": "UNCHANGED"},
        "risk_change": {"direction": "UNCHANGED"},
        "watch_variables": previous.get("thesis", {}).get("watch_variables", []),
        "thesis_risk_conditions": previous.get("thesis", {}).get("thesis_risk_conditions", []),
        "warnings": ["NO_MATERIAL_CHANGE"],
        "data_quality": previous.get("data_quality", {}),
    }


def safe_ticker(ticker: str) -> str:
    return "".join(
        character for character in ticker.upper() if character.isalnum() or character in ".-"
    )


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}-{index}.json")
        if not candidate.exists():
            return candidate
    raise SnapshotReadError
