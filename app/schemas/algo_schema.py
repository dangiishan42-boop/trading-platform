from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.backtest_schema import BacktestMetrics, DataSource, EquityPoint, PositionSizingMode

AlgoConditionSource = Literal["Price", "Open", "High", "Low", "Volume", "RSI", "EMA", "SMA", "MACD", "VWAP", "ATR"]
AlgoOperator = Literal[">", "<", ">=", "<=", "crosses above", "crosses below"]
AlgoConnector = Literal["AND", "OR"]
AlgoSignalType = Literal["buy", "sell", "exit"]
AlgoRuleTimeframe = Literal["Intraday", "Daily", "Weekly", "Monthly"]
AlgoEntryAction = Literal["Buy", "Sell", "Long", "Short"]
AlgoSizingMode = Literal["capital_pct", "quantity", "fixed_quantity", "risk_pct"]
AlgoStopType = Literal["none", "fixed_pct", "atr", "trailing_pct"]
AlgoTargetType = Literal["none", "fixed_pct", "multi_target"]
AlgoExitType = Literal["indicator", "time", "signal_reversal"]


class AlgoRuleCondition(BaseModel):
    signal_type: AlgoSignalType = "buy"
    source: AlgoConditionSource = "Price"
    timeframe: AlgoRuleTimeframe = "Daily"
    operator: AlgoOperator = ">"
    value: float = 0.0
    connector: AlgoConnector = "AND"
    period: int | None = Field(default=None, ge=1, le=300)
    compare_source: AlgoConditionSource | None = None
    compare_period: int | None = Field(default=None, ge=1, le=300)


class AlgoStrategyLeg(BaseModel):
    name: str = "Leg 1"
    conditions: list[AlgoRuleCondition] = Field(default_factory=list, max_length=50)
    connector: AlgoConnector = "AND"


class AlgoPositionSettings(BaseModel):
    action: AlgoEntryAction = "Buy"
    sizing_mode: AlgoSizingMode = "capital_pct"
    capital_allocation_pct: float = Field(default=25.0, gt=0, le=100)
    quantity: int | None = Field(default=None, ge=1)
    fixed_quantity: int | None = Field(default=None, ge=1)
    risk_per_trade_pct: float | None = Field(default=None, gt=0, le=100)


class AlgoTargetLevel(BaseModel):
    target_pct: float = Field(gt=0)
    exit_pct: float = Field(default=100.0, gt=0, le=100)


class AlgoExitSettings(BaseModel):
    stop_type: AlgoStopType = "fixed_pct"
    stop_loss_pct: float | None = Field(default=2.0, gt=0)
    atr_multiplier: float | None = Field(default=2.0, gt=0)
    trailing_stop_pct: float | None = Field(default=None, gt=0)
    target_type: AlgoTargetType = "fixed_pct"
    target_pct: float | None = Field(default=4.0, gt=0)
    targets: list[AlgoTargetLevel] = Field(default_factory=list, max_length=3)
    exit_conditions: list[AlgoRuleCondition] = Field(default_factory=list, max_length=30)
    exit_type: AlgoExitType = "indicator"
    max_bars_in_trade: int | None = Field(default=None, ge=1, le=10000)
    signal_reversal_exit: bool = True


class AlgoSimulationRequest(BaseModel):
    source: DataSource = "sample"
    file_name: str | None = None
    symbol: str = Field(default="DEMO", min_length=1, max_length=24)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    timeframe: str = Field(default="1D", min_length=1, max_length=20)
    from_date: str | None = None
    to_date: str | None = None
    conditions: list[AlgoRuleCondition] = Field(default_factory=list, max_length=50)
    legs: list[AlgoStrategyLeg] = Field(default_factory=list, max_length=10)
    require_all_conditions: bool = True
    position: AlgoPositionSettings = Field(default_factory=AlgoPositionSettings)
    exits: AlgoExitSettings = Field(default_factory=AlgoExitSettings)
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
        if not self.conditions and not any(leg.conditions for leg in self.legs):
            raise ValueError("at least one condition or strategy leg is required")
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
    wins: int = 0
    losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    expectancy: float = 0.0
    validation_warnings: list[str] = Field(default_factory=list)
    metrics: BacktestMetrics
    trades: list[dict[str, Any]]
    equity_curve: list[EquityPoint]


class AlgoCapabilitiesResponse(BaseModel):
    condition_sources: list[str]
    operators: list[str]
    logical_connectors: list[str]
    signal_types: list[str]
    timeframes: list[str] = Field(default_factory=list)
    entry_actions: list[str] = Field(default_factory=list)
    sizing_modes: list[str] = Field(default_factory=list)
    stop_types: list[str] = Field(default_factory=list)
    target_types: list[str] = Field(default_factory=list)
    max_rule_rows: int
    live_execution_enabled: bool = False


class AlgoValidationRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class AlgoValidationResponse(BaseModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SaveAlgoStrategyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)


class SavedAlgoStrategyEntry(BaseModel):
    id: int
    name: str
    symbol: str
    exchange: str
    timeframe: str
    config: dict[str, Any]
    created_at: str
