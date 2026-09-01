from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from importlib import import_module
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ZERO = Decimal("0")
HUNDRED = Decimal("100")
SEC_AGENT = "YouRich/0.5.0 earnings-guidance-research"
SEC_USER_AGENT_WARNING = "SEC_USER_AGENT_NOT_CONFIGURED"
MAX_TICKER_LENGTH = 12
MARKET_QUOTE_TTL_SECONDS = 900
FUNDAMENTALS_TTL_SECONDS = 86400
STALE_FINANCIAL_DAYS = 548
FILING_METADATA_TTL_SECONDS = 86400
FILING_DOCUMENT_TTL_SECONDS = 604800


@dataclass(frozen=True, slots=True)
class ToolError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == ZERO:
        return None
    return numerator / denominator


def percent(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    value = ratio(numerator, denominator)
    if value is None:
        return None
    return value * HUNDRED


def sqrt_decimal(value: Decimal | None) -> Decimal | None:
    if value is None or value < ZERO:
        return None
    with localcontext() as context:
        context.prec = 28
        return value.sqrt()


def clean_ticker(ticker: str) -> str:
    value = ticker.strip().upper()
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    if (
        not value
        or len(value) > MAX_TICKER_LENGTH
        or any(character not in allowed for character in value)
    ):
        raise ToolError(f"invalid ticker: {ticker}")
    return value


def read_payload(path: str | None) -> dict[str, Any]:
    if path is None or path == "-":
        return json.loads(input())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(to_jsonable(payload), indent=2, sort_keys=True))


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    return value


def metric(
    value: Decimal | None,
    formula: str,
    inputs: dict[str, Decimal | None],
    sources: dict[str, str | None] | None = None,
    periods: dict[str, str | None] | None = None,
    evidence_type: str = "derived_metric",
    basis: str | None = None,
) -> dict[str, Any]:
    payload = {
        "type": evidence_type,
        "value": value,
        "formula": formula,
        "inputs": {key: item for key, item in inputs.items() if item is not None},
        "sources": {key: item for key, item in (sources or {}).items() if item is not None},
        "periods": {key: item for key, item in (periods or {}).items() if item is not None},
    }
    if basis is not None:
        payload["basis"] = basis
    return payload


def add_input_arg(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ticker")
    group.add_argument("--input", default="-")


def load_financials(args: argparse.Namespace) -> dict[str, Any]:
    ticker = getattr(args, "ticker", None)
    if ticker:
        sec_module = import_module("_sec")
        fetcher = cast(
            Callable[[str], dict[str, Any]],
            sec_module.fetch_financials,
        )
        return fetcher(ticker)
    return read_payload(getattr(args, "input", "-"))


def fetch_json(url: str, ttl_seconds: int, cache_key: str) -> dict[str, Any]:
    def load() -> dict[str, Any]:
        request = Request(url, headers={"User-Agent": sec_user_agent()})
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ToolError(f"HTTP {exc.code}: {url}") from exc
        except URLError as exc:
            raise ToolError(f"network error: {exc.reason}") from exc
        if not isinstance(payload, dict):
            raise ToolError(f"invalid JSON object: {url}")
        return payload

    return cached_json(cache_key, ttl_seconds, load)


def cached_json(
    cache_key: str,
    ttl_seconds: int,
    loader: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    path = cache_path(cache_key)
    now = time.time()
    if path.exists() and now - path.stat().st_mtime <= ttl_seconds:
        return json.loads(path.read_text(encoding="utf-8"))
    payload = loader()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_jsonable(payload), sort_keys=True), encoding="utf-8")
    return payload


def fetch_text(url: str, ttl_seconds: int, cache_key: str) -> str:
    def load() -> dict[str, Any]:
        request = Request(url, headers={"User-Agent": sec_user_agent()})
        try:
            with urlopen(request, timeout=20) as response:
                return {"text": response.read().decode("utf-8", errors="replace")}
        except HTTPError as exc:
            raise ToolError(f"HTTP {exc.code}: {url}") from exc
        except URLError as exc:
            raise ToolError(f"network error: {exc.reason}") from exc

    payload = cached_json(cache_key, ttl_seconds, load)
    text = payload.get("text")
    if not isinstance(text, str):
        raise ToolError(f"invalid text payload: {url}")
    return text


def cache_path(cache_key: str) -> Path:
    root = Path(os.environ.get("YOURICH_CACHE_DIR", Path.home() / ".cache" / "yourich"))
    safe_key = cache_key.replace("/", "_").replace(":", "_").replace("?", "_")
    return root / f"{safe_key}.json"


def sec_user_agent() -> str:
    configured = os.environ.get("YOURICH_SEC_USER_AGENT", "").strip()
    if not configured:
        return SEC_AGENT
    try:
        configured.encode("latin-1")
    except UnicodeEncodeError as exc:
        raise ToolError("YOURICH_SEC_USER_AGENT must use Latin-1 compatible characters") from exc
    return configured


def sec_user_agent_warnings() -> list[str]:
    if os.environ.get("YOURICH_SEC_USER_AGENT", "").strip():
        return []
    return [SEC_USER_AGENT_WARNING]
