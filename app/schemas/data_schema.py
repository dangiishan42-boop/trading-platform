from datetime import datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataPreviewResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int = Field(ge=0)
    preview_rows: int = Field(ge=0)
    dropped_rows: int = Field(ge=0)
    min_date: str | None = None
    max_date: str | None = None
    source_file: str | None = None


class DataUploadResponse(BaseModel):
    message: str
    file_name: str
    original_file_name: str
    path: str
    preview: DataPreviewResponse


class AngelDataFetchRequest(BaseModel):
    exchange: str = Field(min_length=1, max_length=20)
    symbol_token: str = Field(min_length=1, max_length=64)
    interval: str = Field(min_length=1, max_length=32)
    fromdate: datetime
    todate: datetime

    @field_validator("exchange", "symbol_token", "interval", mode="before")
    @classmethod
    def normalize_string_fields(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(
                "exchange may only contain letters, numbers, underscore, and hyphen"
            )
        return value.upper()

    @field_validator("symbol_token")
    @classmethod
    def validate_symbol_token(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(
                "symbol_token may only contain letters, numbers, underscore, and hyphen"
            )
        return value

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, value: str) -> str:
        normalized = value.upper()
        if not re.fullmatch(r"[A-Z0-9_]+", normalized):
            raise ValueError("interval may only contain letters, numbers, and underscore")
        return normalized

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.todate <= self.fromdate:
            raise ValueError("todate must be later than fromdate")
        return self


class AngelDataFetchResponse(BaseModel):
    message: str
    original_file_name: str
    stored_file_name: str
    path: str
    row_count: int = Field(ge=0)
    min_date: str | None = None
    max_date: str | None = None


HistoricalInterval = Literal["5M", "15M", "30M", "1H", "3H", "4H", "1D"]


class HistoricalDataRequest(BaseModel):
    exchange: str = Field(min_length=1, max_length=20)
    symbol: str | None = Field(default=None, max_length=64)
    symbol_token: str | None = Field(default=None, max_length=64)
    interval: HistoricalInterval
    fromdate: datetime
    todate: datetime

    @field_validator("exchange", "interval", mode="before")
    @classmethod
    def normalize_required_string_fields(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("symbol", "symbol_token", mode="before")
    @classmethod
    def normalize_optional_string_fields(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("exchange")
    @classmethod
    def validate_historical_exchange(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(
                "exchange may only contain letters, numbers, underscore, and hyphen"
            )
        return value.upper()

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[A-Za-z0-9._ -]+", value):
            raise ValueError(
                "symbol may only contain letters, numbers, spaces, dot, underscore, and hyphen"
            )
        return value.upper()

    @field_validator("symbol_token")
    @classmethod
    def validate_historical_symbol_token(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError(
                "symbol_token may only contain letters, numbers, underscore, and hyphen"
            )
        return value

    @field_validator("interval", mode="before")
    @classmethod
    def normalize_historical_interval(cls, value: str) -> str:
        normalized = value.replace(" ", "").upper()
        allowed = {"5M", "15M", "30M", "1H", "3H", "4H", "1D"}
        if normalized not in allowed:
            raise ValueError(f"interval must be one of {sorted(allowed)}")
        return normalized

    @model_validator(mode="after")
    def validate_historical_request(self):
        if self.todate <= self.fromdate:
            raise ValueError("todate must be later than fromdate")
        if not self.symbol_token and not self.symbol:
            raise ValueError("either symbol or symbol_token is required")
        return self


class HistoricalDataRow(BaseModel):
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    change: float | None = None
    change_pct: float | None = None


class HistoricalDataResponse(BaseModel):
    exchange: str
    symbol: str
    symbol_token: str
    interval: HistoricalInterval
    row_count: int = Field(ge=0)
    rows: list[HistoricalDataRow]


class UploadedDatasetEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_file_name: str
    stored_file_name: str
    row_count: int = Field(ge=0)
    min_date: datetime | None = None
    max_date: datetime | None = None
    uploaded_at: datetime
