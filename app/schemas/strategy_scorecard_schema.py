from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StrategyScorecardRequest(BaseModel):
    initial_capital: float = Field(default=100000, gt=0)
    equity_curve: list[dict[str, Any]] = Field(default_factory=list)
    trades: list[dict[str, Any]] = Field(default_factory=list)


class StrategyScorecardResponse(BaseModel):
    metrics: dict[str, float]
    highlights: list[dict[str, Any]]
    warnings: list[str]
    method: str
