from dataclasses import dataclass, field

import pandas as pd

from app.config.constants import OHLCV_COLUMNS


@dataclass
class DataCleaningSummary:
    input_rows: int
    output_rows: int
    dropped_missing_rows: int
    dropped_duplicate_rows: int
    missing_required_counts: dict[str, int] = field(default_factory=dict)
    invalid_date_rows: int = 0
    invalid_numeric_counts: dict[str, int] = field(default_factory=dict)

    @property
    def dropped_rows(self) -> int:
        return self.dropped_missing_rows + self.dropped_duplicate_rows

    def all_rows_removed_reason(self) -> str:
        reasons: list[str] = []

        if self.dropped_missing_rows:
            reasons.append(
                f"{self.dropped_missing_rows} row(s) had missing or invalid required values"
            )
        if self.dropped_duplicate_rows:
            reasons.append(
                f"{self.dropped_duplicate_rows} row(s) were removed as duplicate dates"
            )

        detail_parts: list[str] = []
        if self.invalid_date_rows:
            detail_parts.append(f"date parsing failed for {self.invalid_date_rows} row(s)")

        numeric_details = [
            f"{column}: {count}"
            for column, count in self.invalid_numeric_counts.items()
            if count > 0
        ]
        if numeric_details:
            detail_parts.append(
                "numeric conversion failed for " + ", ".join(numeric_details)
            )

        missing_details = [
            f"{column}: {count}"
            for column, count in self.missing_required_counts.items()
            if count > 0
        ]
        if missing_details:
            detail_parts.append(
                "required-value gaps after normalization in " + ", ".join(missing_details)
            )

        reason_text = "; ".join(reasons) if reasons else "no valid rows remained after normalization"
        detail_text = f" Details: {'; '.join(detail_parts)}." if detail_parts else ""
        return f"All rows were removed during cleaning because {reason_text}.{detail_text}"


class DataCleanerService:
    def clean(
        self,
        df: pd.DataFrame,
        *,
        invalid_date_rows: int = 0,
        invalid_numeric_counts: dict[str, int] | None = None,
    ) -> tuple[pd.DataFrame, DataCleaningSummary]:
        frame = df.copy()
        input_rows = len(frame)
        required_columns = [column for column in ["Date", *OHLCV_COLUMNS] if column in frame.columns]
        missing_required_counts = {
            column: int(frame[column].isna().sum()) for column in required_columns
        }

        if required_columns:
            missing_mask = frame[required_columns].isna().any(axis=1)
            dropped_missing_rows = int(missing_mask.sum())
            frame = frame.loc[~missing_mask].copy()
        else:
            dropped_missing_rows = 0

        if "Date" in frame.columns:
            duplicate_mask = frame.duplicated(subset=["Date"], keep="last")
            dropped_duplicate_rows = int(duplicate_mask.sum())
            frame = frame.loc[~duplicate_mask].copy()
            frame = frame.sort_values("Date").reset_index(drop=True)
        else:
            dropped_duplicate_rows = 0

        summary = DataCleaningSummary(
            input_rows=input_rows,
            output_rows=len(frame),
            dropped_missing_rows=dropped_missing_rows,
            dropped_duplicate_rows=dropped_duplicate_rows,
            missing_required_counts=missing_required_counts,
            invalid_date_rows=invalid_date_rows,
            invalid_numeric_counts=invalid_numeric_counts or {},
        )

        return frame, summary
