from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


HeatmapUniverse = Literal["Nifty 50", "Nifty 100", "Nifty 500", "All NSE", "All BSE"]
HeatmapSizeBy = Literal["Market Cap", "Volume", "Turnover", "Equal Weight"]
HeatmapColorBy = Literal["% Change", "Volume Change", "Relative Volume", "RSI", "Sector Strength"]
HeatmapTimeframe = Literal["1D", "1W", "1M", "3M", "6M", "1Y"]


class HeatmapRunRequest(BaseModel):
    universe: HeatmapUniverse = "Nifty 500"
    size_by: HeatmapSizeBy = "Market Cap"
    color_by: HeatmapColorBy = "% Change"
    timeframe: HeatmapTimeframe = "1D"

    @field_validator("universe", "size_by", "color_by", "timeframe", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return str(value or "").strip()


class HeatmapCapabilitiesResponse(BaseModel):
    universes: list[str]
    size_by: list[str]
    color_by: list[str]
    timeframes: list[str]
    data_source_note: str


class HeatmapStock(BaseModel):
    symbol: str
    name: str
    sector: str
    price: float
    change_pct: float
    market_cap_cr: float
    volume: int
    turnover_cr: float
    rsi: float
    relative_volume: float
    volume_change_pct: float
    size_value: float
    color_value: float


class HeatmapSector(BaseModel):
    name: str
    change_pct: float
    market_cap_cr: float
    volume: int
    stocks: list[HeatmapStock]


class HeatmapRunResponse(BaseModel):
    summary: dict[str, Any]
    sectors: list[HeatmapSector]
    stocks: list[HeatmapStock]
    gainers: list[HeatmapStock]
    losers: list[HeatmapStock]
    breadth: dict[str, Any]
    sector_performance: list[dict[str, Any]]
    distributions: dict[str, Any]
    flows: dict[str, Any]
    indices: list[dict[str, Any]]
    timestamp: str
    data_source_note: str = Field(
        default="Heatmap data is based on local sample data for UI demonstration. Real-time exchange integration coming soon."
    )
