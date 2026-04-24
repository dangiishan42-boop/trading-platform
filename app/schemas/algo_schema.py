from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.backtest_schema import BacktestMetrics, BacktestTrade, DataSource, EquityPoint, PositionSizingMode

AlgoConditionSource = Literal["Price", "EMA", "RSI", "MACD", "Volume"]
AlgoOperator = Literal[">", "<", ">=", "<=", "crosses above", "crosses below"]
AlgoConnector = Literal["AND", "OR"]
AlgoSignalType = Literal["buy", "sell", "exit"]


class AlgoRuleCondition(BaseModel):
    signal_type: AlgoSignalType = "buy"
    source: AlgoConditionSource = "Price"
    operator: AlgoOperator = ">"
    value: float = 0.0
    connector: AlgoConnector = "AND"
    period: int | None = Field(default=None, ge=1, le=300)


class AlgoSimulationRequest(BaseModel):
    source: DataSource = "sample"
    file_name: str | None = None
    symbol: str = Field(default="DEMO", min_length=1, max_length=24)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: str = Field(default="1D", min_length=1, max_length=20)
    from_date: str | None = None
    to_date: str | None = None
    conditions: list[AlgoRuleCondition] = Field(min_length=1, max_length=10)
    require_all_conditions: bool = True
    initial_capital: float = Field(default=100000, gt=0)
    stop_loss_pct: float | None = Field(default=None, gt=0, lt=100)
    target_pct: float | None = Field(default=None, gt=0)
    position_size: float = Field(default=10000, gt=0)
    max_trades_per_day: int = Field(default=5, ge=1, le=100)
    commission_pct: float = Field(default=0.1, ge=0, le=100)
    slippage_pct: float = Field(default=0.0, ge=0, le=100)
    position_sizing_mode: PositionSizingMode = "fixed_capital"

    @field_validator("symbol", "exchange", "timeframe", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized.upper()

    @field_validator("from_date", "to_date", mode="before")
    @classmethod
    def normalize_optional_dates(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_source(self):
        if self.source == "upload" and not self.file_name:
            raise ValueError("file_name is required when source is upload")
        return self


class AlgoSimulationResponse(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    signal_count: int
    buy_signal_count: int
    sell_signal_count: int
    exit_signal_count: int
    estimated_net_profit: float
    estimated_loss: float
    win_rate: float
    max_drawdown: float
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]


class AlgoCapabilitiesResponse(BaseModel):
    condition_sources: list[str]
    operators: list[str]
    logical_connectors: list[str]
    signal_types: list[str]
    max_rule_rows: int
    live_execution_enabled: bool = False
