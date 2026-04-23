import pandas as pd

class DataResamplerService:
    def resample(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        frame = df.copy().set_index("Date")
        agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
        out = frame.resample(rule).agg(agg).dropna().reset_index()
        return out
