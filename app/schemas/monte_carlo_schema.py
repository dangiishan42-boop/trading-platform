from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MonteCarloRunRequest(BaseModel):
    source: Literal["backtest", "optimization"] = "backtest"
    initial_capital: float = Field(default=100000, gt=0)
    simulation_count: Literal[100, 500, 1000] = 500
    drawdown_threshold_pct: float = Field(default=20.0, ge=0)
    noise_pct: float = Field(default=5.0, ge=0, le=50)
    trades: list[dict[str, Any]] = Field(default_factory=list)


class MonteCarloRunResponse(BaseModel):
    simulation_count: int
    trade_count: int
    initial_capital: float
    drawdown_threshold_pct: float
    noise_pct: float
    median_return: float
    worst_case_return: float
    best_case_return: float
    probability_of_loss: float
    probability_of_drawdown_beyond_threshold: float
    robustness_score: float
    distribution: list[dict[str, Any]]
    sample_simulations: list[dict[str, Any]]
