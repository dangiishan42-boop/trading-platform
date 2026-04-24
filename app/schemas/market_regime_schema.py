from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MarketRegimeRunRequest(BaseModel):
    initial_capital: float = Field(default=100000, gt=0)
    slope_threshold_pct: float = Field(default=0.1, ge=0)
    market_data: list[dict[str, Any]] = Field(default_factory=list)
    trades: list[dict[str, Any]] = Field(default_factory=list)


class MarketRegimeRunResponse(BaseModel):
    method: str
    slope_threshold_pct: float
    regime_counts: dict[str, int]
    breakdown: list[dict[str, Any]]
    best_regime: str
    worst_regime: str
    robustness_summary: dict[str, Any]
