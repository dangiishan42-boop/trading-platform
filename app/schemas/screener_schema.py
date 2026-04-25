from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ScreenerCondition = Literal["Greater Than", "Less Than", "Between", "Equal To", "Is True", "Is False"]
ScreenerLogical = Literal["AND", "OR"]
ScreenerSortDirection = Literal["asc", "desc"]


class ScreenerFilter(BaseModel):
    category: str = Field(default="Overview", max_length=80)
    metric: str = Field(max_length=120)
    condition: ScreenerCondition
    value: float | str | bool | None = None
    value_2: float | str | bool | None = None
    logical: ScreenerLogical = "AND"

    @field_validator("category", "metric", mode="before")
    @classmethod
    def normalize_text(cls, value):
        return str(value or "").strip()


class ScreenerRunRequest(BaseModel):
    universe: str = Field(default="Indian Equities", max_length=80)
    exchange: str = Field(default="NSE", max_length=20)
    filters: list[ScreenerFilter] = Field(default_factory=list)
    sort_by: str = Field(default="Market Cap", max_length=80)
    sort_direction: ScreenerSortDirection = "desc"

    @field_validator("universe", "exchange", "sort_by", mode="before")
    @classmethod
    def normalize_request_text(cls, value):
        return str(value or "").strip()

    @field_validator("sort_direction", mode="before")
    @classmethod
    def normalize_sort_direction(cls, value):
        direction = str(value or "desc").strip().lower()
        return "asc" if direction == "asc" else "desc"


class ScreenerSavedScreenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return str(value or "").strip()


class ScreenerResultRow(BaseModel):
    symbol: str
    name: str
    sector: str
    ltp: float
    change_pct: float
    volume: int
    market_cap_cr: float
    pe_ttm: float
    roe_pct: float
    eps_growth_yoy_pct: float
    rsi_14: float
    debt_equity: float
    exchange: str = "NSE"


class ScreenerRunResponse(BaseModel):
    results: list[ScreenerResultRow]
    summary: dict[str, Any]
    distributions: dict[str, Any]
    sector_breakdown: list[dict[str, Any]]
    saved_screens: list[dict[str, Any]] = Field(default_factory=list)
    data_source_note: str


class ScreenerCapabilitiesResponse(BaseModel):
    universes: list[str]
    exchanges: list[str]
    categories: list[str]
    metrics: dict[str, list[str]]
    conditions: list[str]
    logical: list[str]
    sort_options: list[str]
    data_source_note: str
