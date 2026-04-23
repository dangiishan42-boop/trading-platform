from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SavedStrategyConfiguration(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_name: str = Field(index=True)
    display_name: str
    parameters_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
