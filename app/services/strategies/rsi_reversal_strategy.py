from pydantic import Field, model_validator
import pandas as pd

from app.services.indicators.rsi_service import RSIService
from app.services.strategies.base_strategy import BaseStrategy, BaseStrategyParameters


class RSIReversalParameters(BaseStrategyParameters):
    rsi_period: int = Field(default=14, ge=2)
    oversold: float = Field(default=30.0, ge=0.0, le=100.0)
    overbought: float = Field(default=70.0, ge=0.0, le=100.0)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.oversold >= self.overbought:
            raise ValueError("oversold must be smaller than overbought")
        return self


class RSIReversalStrategy(BaseStrategy[RSIReversalParameters]):
    slug = "rsi_reversal"
    name = "RSI Reversal"
    description = "Buys when RSI enters oversold conditions and exits when RSI reaches overbought territory."
    parameter_model = RSIReversalParameters

    def _apply(self, df: pd.DataFrame, parameters: RSIReversalParameters) -> pd.DataFrame:
        frame = df.copy()
        frame["rsi"] = RSIService().calculate(frame["Close"], parameters.rsi_period)
        frame["buy_signal"] = (frame["rsi"] < parameters.oversold) & (frame["rsi"].shift(1) >= parameters.oversold)
        frame["sell_signal"] = (frame["rsi"] > parameters.overbought) & (frame["rsi"].shift(1) <= parameters.overbought)
        return frame
