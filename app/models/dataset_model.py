from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class UploadedDataset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    original_file_name: str
    stored_file_name: str
    row_count: int
    min_date: datetime | None = None
    max_date: datetime | None = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
