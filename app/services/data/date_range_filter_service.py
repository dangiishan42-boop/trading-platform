from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.core.exceptions import DataValidationError, InvalidRequestError


@dataclass(frozen=True)
class DateRangeFilterService:
    date_column: str = "Date"

    def filter(
        self,
        frame: pd.DataFrame,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> pd.DataFrame:
        if not from_date and not to_date:
            return frame

        if self.date_column not in frame.columns:
            raise DataValidationError("Date range filtering requires a Date column")

        start = self._parse_boundary(from_date, "from_date") if from_date else None
        end = self._parse_boundary(to_date, "to_date") if to_date else None
        if start is not None and end is not None and end < start:
            raise InvalidRequestError("to_date must be later than or equal to from_date")

        dates = pd.to_datetime(frame[self.date_column], errors="coerce")
        mask = dates.notna()
        if start is not None:
            mask &= dates >= start
        if end is not None:
            mask &= dates <= end

        filtered = frame.loc[mask].copy()
        if filtered.empty:
            raise DataValidationError("No market data rows found in the selected date range")
        return filtered.reset_index(drop=True)

    def _parse_boundary(self, value: str | None, field_name: str) -> pd.Timestamp:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            raise InvalidRequestError(f"{field_name} must be a valid date or datetime")
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert(None)
        return parsed
