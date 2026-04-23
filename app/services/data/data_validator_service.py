import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from app.config.constants import OHLCV_COLUMNS
from app.core.validators import validate_ohlcv_columns
from app.core.exceptions import DataValidationError


class DataValidatorService:
    def validate(self, df: pd.DataFrame) -> None:
        if df.columns.duplicated().any():
            duplicated = sorted(set(df.columns[df.columns.duplicated()].tolist()))
            raise DataValidationError(f"Duplicate columns are not allowed: {duplicated}")

        validate_ohlcv_columns(list(df.columns))
        if "Date" not in df.columns:
            raise DataValidationError("Date column is required")
        if df.empty:
            raise DataValidationError("Dataframe is empty after normalization and cleaning")
        if not is_datetime64_any_dtype(df["Date"]):
            raise DataValidationError("Date column must contain valid datetime values")
        if df["Date"].isna().any():
            raise DataValidationError("Date column contains missing values")

        for column in OHLCV_COLUMNS:
            if not is_numeric_dtype(df[column]):
                raise DataValidationError(f"Column '{column}' must be numeric")
            if df[column].isna().any():
                raise DataValidationError(f"Column '{column}' contains missing values")
