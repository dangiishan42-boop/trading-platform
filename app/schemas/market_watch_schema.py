from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


MarketWatchInterval = Literal["1m", "5m", "15m", "30m", "1H", "1D"]


class MarketWatchSymbolRequest(BaseModel):
    query: str | None = Field(default=None, max_length=80)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    symbol_token: str | None = Field(default=None, max_length=64)

    @field_validator("query", "symbol_token", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("exchange", mode="before")
    @classmethod
    def normalize_exchange(cls, value):
        return str(value or "NSE").strip().upper()

    @model_validator(mode="after")
    def validate_symbol_source(self):
        if not self.query and not self.symbol_token:
            raise ValueError("query or symbol_token is required")
        return self


class MarketWatchCandleRequest(MarketWatchSymbolRequest):
    interval: MarketWatchInterval = "5m"
    fromdate: datetime | None = None
    todate: datetime | None = None


class MarketWatchQuoteResponse(BaseModel):
    symbol: str
    stock_name: str
    exchange: str
    symbol_token: str | None = None
    latest_price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    last_updated: str | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    volume: float | None = None
    day_range: str | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    vwap: float | None = None
    value_traded: float | None = None
    available: bool = False
    message: str | None = None


class MarketWatchCandleRow(BaseModel):
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketWatchCandleResponse(BaseModel):
    symbol: str
    stock_name: str
    exchange: str
    symbol_token: str
    interval: MarketWatchInterval
    rows: list[MarketWatchCandleRow]


class MarketWatchIndexResponse(BaseModel):
    name: str
    exchange: str
    latest_price: float | None = None
    change: float | None = None
    change_pct: float | None = None
    available: bool = False
    message: str | None = None


class MarketWatchBacktestDatasetResponse(BaseModel):
    message: str
    symbol: str
    stock_name: str
    exchange: str
    symbol_token: str
    stored_file_name: str
    row_count: int
    min_date: str | None = None
    max_date: str | None = None
