from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class SavedStrategy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    description: str = ""
    parameters_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
