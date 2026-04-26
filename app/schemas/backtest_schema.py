from datetime import datetime
import re
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PositionSizingMode = Literal["fixed_quantity", "fixed_capital", "percent_equity"]
TradeExitReason = Literal["signal", "stop_loss", "take_profit", "end_of_data"]
DataSource = Literal["sample", "upload", "fetched"]
BacktestUniverse = Literal["Single Symbol", "Watchlist", "F&O Stocks", "Nifty 50", "Custom List"]
BacktestDataMode = Literal["Equity underlying", "Nearest future"]
OptimizationRankingMetric = Literal[
    "net_profit",
    "total_return_pct",
    "win_rate_pct",
    "max_drawdown_pct",
]

class BacktestRunRequest(BaseModel):
    source: DataSource = "sample"
    file_name: str | None = None
    symbol: str = Field(default="DEMO", min_length=1, max_length=24)
    universe: BacktestUniverse = "Single Symbol"
    symbols: list[str] = Field(default_factory=list)
    data_mode: BacktestDataMode = "Equity underlying"
    timeframe: str = Field(default="1D", min_length=1, max_length=20)
    from_date: str | None = None
    to_date: str | None = None
    strategy_name: str = Field(min_length=1, max_length=64)
    initial_capital: float = Field(default=100000, gt=0)
    commission_pct: float = Field(default=0.1, ge=0, le=100)
    slippage_pct: float = Field(default=0.0, ge=0, le=100)
    stop_loss_pct: float | None = Field(default=None, gt=0, lt=100)
    take_profit_pct: float | None = Field(default=None, gt=0)
    position_sizing_mode: PositionSizingMode = "percent_equity"
    fixed_quantity: int | None = Field(default=None, ge=1)
    capital_per_trade: float | None = Field(default=None, gt=0)
    equity_pct_per_trade: float | None = Field(default=None, gt=0, le=100)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_position_sizing_fields(cls, value: Any):
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        if normalized.get("equity_pct_per_trade") is None and normalized.get("percent_of_equity") is not None:
            normalized["equity_pct_per_trade"] = normalized["percent_of_equity"]
        if normalized.get("capital_per_trade") is None and normalized.get("fixed_capital_per_trade") is not None:
            normalized["capital_per_trade"] = normalized["fixed_capital_per_trade"]
        return normalized

    @field_validator("source", "symbol", "timeframe", "strategy_name", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            raise ValueError("symbol may only contain letters, numbers, dot, underscore, and hyphen")
        return value.upper()

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            raise ValueError("timeframe may only contain letters, numbers, dot, underscore, and hyphen")
        return value

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9_]+", value.lower()):
            raise ValueError("strategy_name must be a slug using lowercase letters, numbers, and underscores")
        return value.lower()

    @field_validator("from_date", "to_date", mode="before")
    @classmethod
    def normalize_optional_date_fields(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_position_sizing(self):
        if self.source == "upload" and not self.file_name:
            raise ValueError("file_name is required when source is upload")
        if self.position_sizing_mode == "fixed_quantity" and self.fixed_quantity is None:
            raise ValueError("fixed_quantity is required when position_sizing_mode is fixed_quantity")
        if self.position_sizing_mode == "fixed_capital" and self.capital_per_trade is None:
            raise ValueError("capital_per_trade is required when position_sizing_mode is fixed_capital")
        if self.position_sizing_mode == "percent_equity" and self.equity_pct_per_trade is None:
            self.equity_pct_per_trade = 100.0
        return self

class BacktestTrade(BaseModel):
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    exit_reason: TradeExitReason
    position_sizing_mode: PositionSizingMode
    quantity: int
    capital_used: float
    gross_pnl: float
    brokerage_cost: float
    slippage_cost: float
    pnl: float
    return_pct: float

class BacktestMetrics(BaseModel):
    total_return_pct: float
    net_profit: float
    total_trades: int
    win_rate_pct: float
    max_drawdown_pct: float
    ending_equity: float
    total_brokerage: float
    total_slippage: float
    total_costs: float

class EquityPoint(BaseModel):
    timestamp: str
    equity: float


class MarketDataPoint(BaseModel):
    timestamp: str
    close: float

class BacktestRunResponse(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    from_date: str | None = None
    to_date: str | None = None
    commission_pct: float
    slippage_pct: float
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    position_sizing_mode: PositionSizingMode
    fixed_quantity: int | None = None
    capital_per_trade: float | None = None
    equity_pct_per_trade: float | None = None
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]
    market_data: list[MarketDataPoint] = Field(default_factory=list)
    chart_html: str
    drawdown_chart_html: str


class BacktestExportRequest(BaseModel):
    strategy_name: str
    symbol: str
    timeframe: str
    commission_pct: float = 0.0
    slippage_pct: float = 0.0
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    position_sizing_mode: PositionSizingMode = "percent_equity"
    fixed_quantity: int | None = None
    capital_per_trade: float | None = None
    equity_pct_per_trade: float | None = None
    metrics: BacktestMetrics
    trades: list[BacktestTrade]


class BacktestHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_name: str
    symbol: str
    timeframe: str
    initial_capital: float
    commission_pct: float
    slippage_pct: float
    total_return_pct: float
    win_rate_pct: float
    max_drawdown_pct: float
    created_at: datetime
