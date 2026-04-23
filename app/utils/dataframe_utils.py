import pandas as pd

def head_records(df: pd.DataFrame, n: int = 5) -> list[dict]:
    return df.head(n).to_dict(orient="records")
