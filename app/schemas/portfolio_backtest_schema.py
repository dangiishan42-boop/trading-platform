from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.backtest_schema import (
    BacktestMetrics,
    BacktestTrade,
    DataSource,
    EquityPoint,
    PositionSizingMode,
)

RebalancingMode = Literal["none", "monthly", "quarterly"]


class PortfolioBacktestDataset(BaseModel):
    source: DataSource = "sample"
    file_name: str | None = None
    symbol: str = Field(min_length=1, max_length=24)
    timeframe: str = Field(default="1D", min_length=1, max_length=20)
    allocation_pct: float = Field(gt=0, le=100)

    @field_validator("source", "symbol", "timeframe", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        from app.schemas.backtest_schema import BacktestRunRequest

        return BacktestRunRequest(
            source="sample",
            symbol=value,
            timeframe="1D",
            strategy_name="ema_crossover",
        ).symbol

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        from app.schemas.backtest_schema import BacktestRunRequest

        return BacktestRunRequest(
            source="sample",
            symbol="DEMO",
            timeframe=value,
            strategy_name="ema_crossover",
        ).timeframe

    @model_validator(mode="after")
    def validate_dataset_source(self):
        if self.source == "upload" and not self.file_name:
            raise ValueError("file_name is required when source is upload")
        return self


class PortfolioBacktestRequest(BaseModel):
    datasets: list[PortfolioBacktestDataset] = Field(min_length=2)
    strategy_name: str = Field(min_length=1, max_length=64)
    rebalancing_mode: RebalancingMode = "none"
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

    @field_validator("strategy_name", mode="before")
    @classmethod
    def normalize_strategy_name(cls, value: Any) -> str:
        from app.schemas.backtest_schema import BacktestRunRequest

        return BacktestRunRequest(
            source="sample",
            symbol="DEMO",
            timeframe="1D",
            strategy_name=value,
        ).strategy_name

    @field_validator("rebalancing_mode", mode="before")
    @classmethod
    def normalize_rebalancing_mode(cls, value: Any) -> str:
        normalized = str(value or "none").strip().lower()
        if not normalized:
            return "none"
        return normalized

    @model_validator(mode="after")
    def validate_portfolio(self):
        allocation_total = sum(dataset.allocation_pct for dataset in self.datasets)
        if abs(allocation_total - 100.0) > 0.01:
            raise ValueError("dataset allocation_pct values must total 100")
        if self.position_sizing_mode == "fixed_quantity" and self.fixed_quantity is None:
            raise ValueError("fixed_quantity is required when position_sizing_mode is fixed_quantity")
        if self.position_sizing_mode == "fixed_capital" and self.capital_per_trade is None:
            raise ValueError("capital_per_trade is required when position_sizing_mode is fixed_capital")
        if self.position_sizing_mode == "percent_equity" and self.equity_pct_per_trade is None:
            self.equity_pct_per_trade = 100.0
        return self


class PortfolioSymbolResult(BaseModel):
    symbol: str
    source: DataSource
    file_name: str | None = None
    timeframe: str
    allocation_pct: float
    allocated_capital: float
    metrics: BacktestMetrics
    trades: list[BacktestTrade]
    equity_curve: list[EquityPoint]


class PortfolioBacktestResponse(BaseModel):
    strategy_name: str
    rebalancing_mode: RebalancingMode = "none"
    initial_capital: float
    metrics: BacktestMetrics
    equity_curve: list[EquityPoint]
    symbol_results: list[PortfolioSymbolResult]
