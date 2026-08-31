from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _core import (
    MARKET_QUOTE_TTL_SECONDS,
    ToolError,
    cached_json,
    clean_ticker,
    decimal_or_none,
    fetch_json,
)


@dataclass(frozen=True, slots=True)
class MarketQuote:
    ticker: str
    price: Decimal
    currency: str
    timestamp: str
    source: str
    is_delayed: bool
    provider: str

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "currency": self.currency,
            "timestamp": self.timestamp,
            "source": self.source,
            "is_delayed": self.is_delayed,
            "provider": self.provider,
        }


class MarketDataProvider(Protocol):
    def get_quote(self, _ticker: str) -> MarketQuote: ...


@dataclass(frozen=True, slots=True)
class YahooChartProvider:
    def get_quote(self, ticker: str) -> MarketQuote:
        symbol = clean_ticker(ticker)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
        payload = fetch_json(url, MARKET_QUOTE_TTL_SECONDS, f"market_yahoo_{symbol}")
        result = payload.get("chart", {}).get("result", [])
        if not isinstance(result, list) or not result:
            raise ToolError(f"Yahoo chart returned no quote for {symbol}")
        meta = result[0].get("meta", {})
        price = decimal_or_none(meta.get("regularMarketPrice"))
        timestamp = meta.get("regularMarketTime")
        currency = meta.get("currency")
        if price is None or not isinstance(timestamp, int) or not isinstance(currency, str):
            raise ToolError(f"Yahoo chart quote is incomplete for {symbol}")
        return MarketQuote(
            ticker=symbol,
            price=price,
            currency=currency,
            timestamp=datetime.fromtimestamp(timestamp, UTC).date().isoformat(),
            source=url,
            is_delayed=True,
            provider="yahoo-chart-unofficial",
        )


@dataclass(frozen=True, slots=True)
class StooqCsvProvider:
    def get_quote(self, ticker: str) -> MarketQuote:
        symbol = clean_ticker(ticker)
        stooq_symbol = f"{symbol.lower()}.us"
        url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2c&h&e=csv"

        def load() -> dict[str, Any]:
            try:
                with urlopen(
                    Request(url, headers={"User-Agent": "YouRich/0.2"}), timeout=20
                ) as response:
                    return {"csv": response.read().decode("utf-8")}
            except HTTPError as exc:
                raise ToolError(f"HTTP {exc.code}: {url}") from exc
            except URLError as exc:
                raise ToolError(f"network error: {exc.reason}") from exc

        payload = cached_json(f"market_stooq_{symbol}", MARKET_QUOTE_TTL_SECONDS, load)
        rows = list(csv.DictReader(StringIO(str(payload.get("csv", "")))))
        if not rows:
            raise ToolError(f"Stooq returned no quote for {symbol}")
        row = rows[0]
        price = decimal_or_none(row.get("Close"))
        date = row.get("Date")
        if price is None or not isinstance(date, str) or date == "N/D":
            raise ToolError(f"Stooq quote is incomplete for {symbol}")
        return MarketQuote(
            ticker=symbol,
            price=price,
            currency="USD",
            timestamp=date,
            source=url,
            is_delayed=True,
            provider="stooq-csv-unofficial",
        )


@dataclass(frozen=True, slots=True)
class AlphaVantageProvider:
    api_key: str

    def get_quote(self, ticker: str) -> MarketQuote:
        symbol = clean_ticker(ticker)
        url = (
            "https://www.alphavantage.co/query?function=GLOBAL_QUOTE"
            f"&symbol={symbol}&apikey={self.api_key}"
        )
        payload = fetch_json(url, MARKET_QUOTE_TTL_SECONDS, f"market_alpha_vantage_{symbol}")
        quote = payload.get("Global Quote", {})
        price = decimal_or_none(quote.get("05. price") if isinstance(quote, dict) else None)
        day = quote.get("07. latest trading day") if isinstance(quote, dict) else None
        if price is None or not isinstance(day, str):
            raise ToolError(f"Alpha Vantage quote is incomplete for {symbol}")
        return MarketQuote(
            ticker=symbol,
            price=price,
            currency="USD",
            timestamp=day,
            source="https://www.alphavantage.co/query?function=GLOBAL_QUOTE",
            is_delayed=True,
            provider="alpha-vantage",
        )


def get_market_quote(ticker: str) -> tuple[dict[str, object] | None, list[str]]:
    warnings = []
    for provider in configured_providers():
        try:
            return provider.get_quote(ticker).to_dict(), warnings
        except ToolError as exc:
            warnings.append(str(exc))
    return None, warnings


def configured_providers() -> list[MarketDataProvider]:
    requested = os.environ.get("YOURICH_MARKET_PROVIDER", "").strip().lower()
    api_key = os.environ.get("YOURICH_MARKET_API_KEY", "").strip()
    if requested == "alpha_vantage" and api_key:
        return [AlphaVantageProvider(api_key), YahooChartProvider(), StooqCsvProvider()]
    if requested == "stooq":
        return [StooqCsvProvider(), YahooChartProvider()]
    return [YahooChartProvider(), StooqCsvProvider()]
