from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint

@dataclass
class MarketDataMetadata:
    symbol: str
    timeframe: str
    rows: int


class FnoQuoteCache(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("symbol", name="uq_fno_quote_cache_symbol"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, max_length=80)
    name: str | None = Field(default=None, max_length=200)
    exchange: str = Field(default="NSE", index=True, max_length=20)
    token: str | None = Field(default=None, index=True, max_length=64)
    ltp: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    point_change: float | None = None
    percent_change: float | None = None
    volume: float | None = None
    last_updated: datetime = Field(default_factory=datetime.utcnow, index=True)
    source: str = Field(default="Cached", max_length=40)
    failure_message: str | None = Field(default=None, max_length=500)
