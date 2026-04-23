from collections import Counter

from app.config.constants import OHLCV_COLUMNS
from app.core.exceptions import DataValidationError


def validate_ohlcv_columns(columns: list[str]) -> None:
    normalized_columns = [column.strip() for column in columns]
    duplicates = sorted(
        column for column, count in Counter(normalized_columns).items() if count > 1
    )
    if duplicates:
        raise DataValidationError(f"Duplicate columns are not allowed: {duplicates}")

    missing = [col for col in OHLCV_COLUMNS if col not in normalized_columns]
    if missing:
        raise DataValidationError(f"Missing required OHLCV columns: {missing}")
