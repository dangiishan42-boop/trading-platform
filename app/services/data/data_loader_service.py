import re
import secrets
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd

from app.config.constants import DATE_COLUMN_CANDIDATES
from app.config.paths import RAW_DATA_DIR, SAMPLE_DATA_DIR
from app.config.settings import get_settings
from app.core.exceptions import DataValidationError, InvalidRequestError
from app.schemas.data_schema import DataPreviewResponse, DataUploadResponse
from app.services.data.data_cleaner_service import DataCleanerService, DataCleaningSummary
from app.services.data.data_validator_service import DataValidatorService


class DataLoaderService:
    PREVIEW_ROW_LIMIT = 20
    REQUIRED_NUMERIC_COLUMNS = ("Open", "High", "Low", "Close", "Volume")
    MISSING_TEXT_VALUES = {"", "nan", "none", "null", "nat"}

    def __init__(self) -> None:
        self.settings = get_settings()
        self.validator = DataValidatorService()
        self.cleaner = DataCleanerService()

    def _read_csv(self, source: str | Path | BytesIO) -> pd.DataFrame:
        try:
            return pd.read_csv(source)
        except pd.errors.EmptyDataError as exc:
            raise DataValidationError("CSV file is empty") from exc
        except pd.errors.ParserError as exc:
            raise DataValidationError("Unable to parse CSV file") from exc
        except UnicodeDecodeError as exc:
            raise DataValidationError("CSV file encoding is not supported") from exc

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(column).strip() for column in df.columns]
        date_candidates = {candidate.lower() for candidate in DATE_COLUMN_CANDIDATES}

        date_columns = [column for column in df.columns if column.lower() in date_candidates]
        if len(date_columns) > 1:
            raise DataValidationError(f"Multiple date columns found: {date_columns}")
        if not date_columns:
            raise DataValidationError(
                "No supported date column was found. "
                f"Expected one of {sorted(DATE_COLUMN_CANDIDATES)} but found {list(df.columns)}"
            )

        market_column_groups: dict[str, list[str]] = {}
        for column in df.columns:
            normalized = column.lower()
            if normalized in {"open", "high", "low", "close", "volume"}:
                market_column_groups.setdefault(normalized, []).append(column)

        duplicated_market_columns = [
            group[0].capitalize()
            for group in market_column_groups.values()
            if len(group) > 1
        ]
        if duplicated_market_columns:
            raise DataValidationError(
                f"Duplicate OHLCV columns found: {sorted(duplicated_market_columns)}"
            )

        rename_map = {}
        if date_columns:
            rename_map[date_columns[0]] = "Date"
        for column in df.columns:
            normalized = column.lower()
            if normalized in {"open", "high", "low", "close", "volume"}:
                rename_map[column] = normalized.capitalize()

        df = df.rename(columns=rename_map)
        return df

    def _normalize_text_series(self, series: pd.Series) -> pd.Series:
        normalized = series.astype("string").str.strip()
        return normalized.mask(normalized.str.lower().isin(self.MISSING_TEXT_VALUES), pd.NA)

    def _parse_dates(self, series: pd.Series) -> tuple[pd.Series, int]:
        normalized = self._normalize_text_series(series)
        present_mask = normalized.notna()
        try:
            parsed = pd.to_datetime(normalized, errors="coerce", utc=True, format="mixed")
        except (TypeError, ValueError) as exc:
            raise DataValidationError("Unable to parse the date column") from exc

        invalid_rows = int((parsed.isna() & present_mask).sum())
        return parsed.dt.tz_localize(None), invalid_rows

    def _convert_numeric_column(self, series: pd.Series, column_name: str) -> tuple[pd.Series, int]:
        normalized = self._normalize_text_series(series)
        normalized = normalized.str.replace(",", "", regex=False)
        converted = pd.to_numeric(normalized, errors="coerce")
        invalid_rows = int((converted.isna() & normalized.notna()).sum())
        return converted, invalid_rows

    def _raise_if_all_rows_removed(self, summary: DataCleaningSummary) -> None:
        if summary.input_rows > 0 and summary.output_rows == 0:
            raise DataValidationError(summary.all_rows_removed_reason())

    def _normalize(self, df: pd.DataFrame) -> tuple[pd.DataFrame, DataCleaningSummary]:
        frame = self._normalize_columns(df)
        invalid_date_rows = 0
        if "Date" in frame.columns:
            frame["Date"], invalid_date_rows = self._parse_dates(frame["Date"])

        invalid_numeric_counts: dict[str, int] = {}
        for column in self.REQUIRED_NUMERIC_COLUMNS:
            if column in frame.columns:
                frame[column], invalid_numeric_counts[column] = self._convert_numeric_column(
                    frame[column], column
                )

        cleaned_frame, summary = self.cleaner.clean(
            frame,
            invalid_date_rows=invalid_date_rows,
            invalid_numeric_counts=invalid_numeric_counts,
        )
        self._raise_if_all_rows_removed(summary)
        self.validator.validate(cleaned_frame)
        return cleaned_frame, summary

    def _uploaded_path(self, file_name: str) -> Path:
        if not file_name:
            raise InvalidRequestError("file_name is required when source='upload'")

        safe_name = Path(file_name).name
        if safe_name != file_name:
            raise InvalidRequestError("Only filenames inside the upload directory are allowed")
        if Path(safe_name).suffix.lower() != ".csv":
            raise InvalidRequestError("Only CSV files are supported")

        return RAW_DATA_DIR / safe_name

    def _safe_upload_name(self, file_name: str | None) -> str:
        if not file_name:
            raise InvalidRequestError("Uploaded file must include a filename")

        safe_name = Path(file_name).name
        if safe_name != file_name:
            raise InvalidRequestError("Nested upload paths are not allowed")
        if Path(safe_name).suffix.lower() != ".csv":
            raise InvalidRequestError("Only CSV files are supported")
        return safe_name

    def _validate_upload_content_type(self, content_type: str | None) -> None:
        if not content_type:
            return

        normalized = content_type.split(";", 1)[0].strip().lower()
        if normalized not in {item.lower() for item in self.settings.allowed_upload_content_types}:
            raise InvalidRequestError("Unsupported upload content type. Only CSV uploads are allowed")

    def _validate_upload_bytes(self, content: bytes) -> None:
        if not content:
            raise InvalidRequestError("Uploaded file is empty")

        if len(content) > self.settings.max_upload_size_bytes:
            raise InvalidRequestError(
                f"Uploaded file is too large. Maximum allowed size is {self.settings.max_upload_size_mb} MB"
            )

        if b"\x00" in content:
            raise InvalidRequestError("Uploaded file appears to be binary data and is not a valid CSV")

    def _generated_upload_name(self, original_file_name: str) -> str:
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(original_file_name).stem).strip("._-")
        safe_stem = (stem or "upload")[:80]
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        token = secrets.token_hex(4)
        return f"{safe_stem}_{timestamp}_{token}.csv"

    def _store_upload(self, destination: Path, content: bytes) -> None:
        temp_path = destination.with_suffix(f"{destination.suffix}.part")
        if temp_path.exists():
            temp_path.unlink()
        temp_path.write_bytes(content)
        temp_path.replace(destination)

    def _serialize_timestamp(self, value: pd.Timestamp | None) -> str | None:
        if value is None or pd.isna(value):
            return None
        return value.to_pydatetime().isoformat()

    def _prepare_frame(self, df: pd.DataFrame) -> tuple[pd.DataFrame, DataCleaningSummary]:
        return self._normalize(df)

    def load_sample(self) -> pd.DataFrame:
        path = SAMPLE_DATA_DIR / "sample_ohlcv.csv"
        if not path.exists():
            raise FileNotFoundError("Sample data file not found: sample_ohlcv.csv")
        frame, _ = self._prepare_frame(self._read_csv(path))
        return frame

    def load_uploaded(self, file_name: str) -> pd.DataFrame:
        path = self._uploaded_path(file_name)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path.name}")
        frame, _ = self._prepare_frame(self._read_csv(path))
        return frame

    def load(self, source: str, file_name: str | None = None) -> pd.DataFrame:
        normalized_source = source.strip().lower()
        if normalized_source == "sample":
            return self.load_sample()
        if normalized_source == "upload":
            return self.load_uploaded(file_name or "")
        raise InvalidRequestError("source must be either 'sample' or 'upload'")

    def preview_sample(self) -> DataPreviewResponse:
        path = SAMPLE_DATA_DIR / "sample_ohlcv.csv"
        if not path.exists():
            raise FileNotFoundError("Sample data file not found: sample_ohlcv.csv")
        frame, summary = self._prepare_frame(self._read_csv(path))
        return self._preview(frame, summary, source_file=path.name)

    def preview_uploaded(self, file_name: str) -> DataPreviewResponse:
        path = self._uploaded_path(file_name)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path.name}")
        frame, summary = self._prepare_frame(self._read_csv(path))
        return self._preview(frame, summary, source_file=path.name)

    def save_upload(self, file_name: str | None, content: bytes, content_type: str | None = None) -> DataUploadResponse:
        original_file_name = self._safe_upload_name(file_name)
        self._validate_upload_content_type(content_type)
        self._validate_upload_bytes(content)

        frame, summary = self._prepare_frame(self._read_csv(BytesIO(content)))

        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        stored_name = self._generated_upload_name(original_file_name)
        destination = RAW_DATA_DIR / stored_name
        self._store_upload(destination, content)

        return DataUploadResponse(
            message="File uploaded successfully",
            file_name=stored_name,
            original_file_name=original_file_name,
            path=str(destination),
            preview=self._preview(frame, summary, source_file=stored_name),
        )

    def _preview(
        self,
        df: pd.DataFrame,
        summary: DataCleaningSummary,
        source_file: str | None = None,
    ) -> DataPreviewResponse:
        records = df.head(self.PREVIEW_ROW_LIMIT).copy()
        if "Date" in records.columns:
            records["Date"] = records["Date"].map(self._serialize_timestamp)
        records = records.where(pd.notna(records), None)
        rows = records.to_dict(orient="records")
        return DataPreviewResponse(
            columns=list(df.columns),
            rows=rows,
            total_rows=len(df),
            preview_rows=len(rows),
            dropped_rows=summary.dropped_rows,
            min_date=self._serialize_timestamp(df["Date"].min() if not df.empty else None),
            max_date=self._serialize_timestamp(df["Date"].max() if not df.empty else None),
            source_file=source_file,
        )
