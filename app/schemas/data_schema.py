from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class UploadedDatasetEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_file_name: str
    stored_file_name: str
    row_count: int = Field(ge=0)
    min_date: datetime | None = None
    max_date: datetime | None = None
    uploaded_at: datetime
