import pandas as pd

class SMAService:
    def calculate(self, series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()
