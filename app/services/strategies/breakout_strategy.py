from pydantic import Field
import pandas as pd

from app.services.strategies.base_strategy import BaseStrategy, BaseStrategyParameters


class BreakoutParameters(BaseStrategyParameters):
    lookback: int = Field(default=20, ge=2)


class BreakoutStrategy(BaseStrategy[BreakoutParameters]):
    slug = "breakout"
    name = "Breakout"
    description = "Buys when price breaks above the rolling high and exits when it falls below the rolling low."
    parameter_model = BreakoutParameters

    def _apply(self, df: pd.DataFrame, parameters: BreakoutParameters) -> pd.DataFrame:
        frame = df.copy()
        highest = frame["High"].rolling(parameters.lookback).max().shift(1)
        lowest = frame["Low"].rolling(parameters.lookback).min().shift(1)
        frame["buy_signal"] = frame["Close"] > highest
        frame["sell_signal"] = frame["Close"] < lowest
        return frame
