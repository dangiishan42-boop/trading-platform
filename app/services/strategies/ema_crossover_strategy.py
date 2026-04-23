from pydantic import Field, model_validator
import pandas as pd

from app.services.indicators.ema_service import EMAService
from app.services.strategies.base_strategy import BaseStrategy, BaseStrategyParameters


class EMACrossoverParameters(BaseStrategyParameters):
    fast_period: int = Field(default=20, ge=1)
    slow_period: int = Field(default=50, ge=2)

    @model_validator(mode="after")
    def validate_period_order(self):
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be smaller than slow_period")
        return self


class EMACrossoverStrategy(BaseStrategy[EMACrossoverParameters]):
    slug = "ema_crossover"
    name = "EMA Crossover"
    description = "Buys when the fast EMA crosses above the slow EMA and exits on the opposite cross."
    parameter_model = EMACrossoverParameters

    def _apply(self, df: pd.DataFrame, parameters: EMACrossoverParameters) -> pd.DataFrame:
        frame = df.copy()
        ema = EMAService()
        frame["fast_ema"] = ema.calculate(frame["Close"], parameters.fast_period)
        frame["slow_ema"] = ema.calculate(frame["Close"], parameters.slow_period)
        frame["buy_signal"] = (frame["fast_ema"] > frame["slow_ema"]) & (frame["fast_ema"].shift(1) <= frame["slow_ema"].shift(1))
        frame["sell_signal"] = (frame["fast_ema"] < frame["slow_ema"]) & (frame["fast_ema"].shift(1) >= frame["slow_ema"].shift(1))
        return frame
