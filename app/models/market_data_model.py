from dataclasses import dataclass

@dataclass
class MarketDataMetadata:
    symbol: str
    timeframe: str
    rows: int
