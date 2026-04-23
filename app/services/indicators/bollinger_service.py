import pandas as pd

class BollingerService:
    def calculate(self, series: pd.Series, period: int = 20, std_multiplier: float = 2.0) -> pd.DataFrame:
        sma = series.rolling(period).mean()
        std = series.rolling(period).std()
        return pd.DataFrame({
            "middle_band": sma,
            "upper_band": sma + std_multiplier * std,
            "lower_band": sma - std_multiplier * std,
        })
