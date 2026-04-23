from pathlib import Path
import pandas as pd

class DataExportService:
    def to_csv(self, df: pd.DataFrame, path: Path) -> Path:
        df.to_csv(path, index=False)
        return path
