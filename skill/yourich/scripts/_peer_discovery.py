from __future__ import annotations

from typing import Final

AUTO_PEERS: Final = {
    "NVDA": ("AMD", "AVGO", "INTC"),
    "AMD": ("NVDA", "AVGO", "INTC"),
    "AVGO": ("NVDA", "AMD", "INTC"),
    "INTC": ("NVDA", "AMD", "AVGO"),
    "AAPL": ("MSFT", "GOOGL"),
    "MSFT": ("AAPL", "GOOGL"),
    "GOOGL": ("AAPL", "MSFT"),
    "WMT": ("COST", "TGT"),
    "COST": ("WMT", "TGT"),
    "TGT": ("WMT", "COST"),
    "KO": ("PEP",),
    "PEP": ("KO",),
}


def automatic_peer_tickers(ticker: str) -> list[str]:
    return list(AUTO_PEERS.get(ticker.upper(), ()))
