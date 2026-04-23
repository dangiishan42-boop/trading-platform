import pandas as pd

class VolumeService:
    def average(self, volume: pd.Series, period: int = 20) -> pd.Series:
        return volume.rolling(period).mean()
