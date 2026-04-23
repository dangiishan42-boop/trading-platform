import pandas as pd

class EMAService:
    def calculate(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()
