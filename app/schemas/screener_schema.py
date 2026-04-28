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

    @field_validator("condition", mode="before")
    @classmethod
    def normalize_condition(cls, value):
        aliases = {
            "greater_than": "Greater Than",
            "greater than": "Greater Than",
            "less_than": "Less Than",
            "less than": "Less Than",
            "between": "Between",
            "equal_to": "Equal To",
            "equal to": "Equal To",
            "is_true": "Is True",
            "is true": "Is True",
            "is_false": "Is False",
            "is false": "Is False",
        }
        text = str(value or "").strip()
        return aliases.get(text.lower(), text)


class ScreenerRunRequest(BaseModel):
    universe: str = Field(default="Indian Equities", max_length=80)
    exchange: str = Field(default="NSE", max_length=20)
    filters: list[ScreenerFilter] = Field(default_factory=list)
    sort_by: str = Field(default="Market Cap", max_length=80)
    sort_direction: ScreenerSortDirection = "desc"
    custom_formula_name: str | None = Field(default=None, max_length=120)
    custom_formula_expression: str | None = None
    custom_formula_enabled: bool = False

    @field_validator("universe", "exchange", "sort_by", "custom_formula_name", mode="before")
    @classmethod
    def normalize_request_text(cls, value):
        if value is None:
            return None
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


class ScreenerFormulaValidateRequest(BaseModel):
    expression: str = Field(default="")


class ScreenerFormulaValidateResponse(BaseModel):
    valid: bool
    normalized_expression: str
    errors: list[str] = Field(default_factory=list)
    referenced_metrics: list[str] = Field(default_factory=list)


class ScreenerResultRow(BaseModel):
    symbol: str
    name: str
    sector: str
    ltp: float | None = None
    previous_close: float | None = None
    percent_change: float | None = None
    change_pct: float | None = None
    point_change: float | None = None
    volume: float | None = None
    avg_volume_20d: float | None = None
    relative_volume: float | None = None
    volume_spike: bool | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    distance_from_52w_high_pct: float | None = None
    distance_from_52w_low_pct: float | None = None
    gap_up_pct: float | None = None
    gap_down_pct: float | None = None
    day_range_pct: float | None = None
    turnover: float | None = None
    data_source: str = "Unavailable"
    market_cap_cr: float
    pe_ttm: float
    roe_pct: float
    eps_growth_yoy_pct: float
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    price_above_ema20: bool | None = None
    price_above_ema50: bool | None = None
    price_above_ema200: bool | None = None
    ema20_above_ema50: bool | None = None
    ema50_above_ema200: bool | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    price_above_sma20: bool | None = None
    price_above_sma50: bool | None = None
    price_above_sma200: bool | None = None
    rsi_14: float | None = None
    rsi_status: str | None = None
    rsi_oversold: bool | None = None
    rsi_overbought: bool | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    macd_bullish: bool | None = None
    macd_bearish: bool | None = None
    breakout_20d: bool | None = None
    breakdown_20d: bool | None = None
    breakout_52w: bool | None = None
    breakdown_52w: bool | None = None
    volume_confirmed_breakout: bool | None = None
    trend_score: float | None = None
    technical_rating: str | None = None
    doji: bool | None = None
    hammer: bool | None = None
    shooting_star: bool | None = None
    bullish_engulfing: bool | None = None
    bearish_engulfing: bool | None = None
    inside_bar: bool | None = None
    outside_bar: bool | None = None
    bullish_marubozu: bool | None = None
    bearish_marubozu: bool | None = None
    gap_up: bool | None = None
    gap_down: bool | None = None
    strong_bullish_candle: bool | None = None
    strong_bearish_candle: bool | None = None
    detected_patterns: list[str] = Field(default_factory=list)
    bullish_pattern_count: int = 0
    bearish_pattern_count: int = 0
    neutral_pattern_count: int = 0
    candlestick_bias: str = "Unavailable"
    pattern_status: str = "Unavailable"
    formula_match: bool | None = None
    composite_score: float | None = None
    debt_equity: float
    exchange: str = "NSE"


class ScreenerRunResponse(BaseModel):
    results: list[ScreenerResultRow]
    summary: dict[str, Any]
    distributions: dict[str, Any]
    sector_breakdown: list[dict[str, Any]]
    saved_screens: list[dict[str, Any]] = Field(default_factory=list)
    data_source_note: str
    formula_validation: dict[str, Any] | None = None
    formula_matched_count: int | None = None
    formula_errors: list[str] = Field(default_factory=list)


class ScreenerCapabilitiesResponse(BaseModel):
    universes: list[str]
    exchanges: list[str]
    categories: list[str]
    metrics: dict[str, list[str]]
    conditions: list[str]
    logical: list[str]
    sort_options: list[str]
    quick_filters: list[dict[str, Any]] = Field(default_factory=list)
    formula_presets: list[dict[str, Any]] = Field(default_factory=list)
    data_source_note: str
