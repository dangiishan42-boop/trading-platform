import pandas as pd

class CsvService:
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_csv(path)
