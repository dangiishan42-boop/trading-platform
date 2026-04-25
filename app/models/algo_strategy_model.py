from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class SavedAlgoStrategy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    symbol: str = Field(index=True)
    exchange: str = "NSE"
    timeframe: str = "1D"
    config_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
