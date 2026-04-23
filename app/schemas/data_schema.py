from datetime import datetime
import re
from typing import Any

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


class UploadedDatasetEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_file_name: str
    stored_file_name: str
    row_count: int = Field(ge=0)
    min_date: datetime | None = None
    max_date: datetime | None = None
    uploaded_at: datetime
