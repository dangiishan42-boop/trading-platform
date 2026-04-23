from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class BacktestResultRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_name: str
    symbol: str
    total_return_pct: float
    win_rate_pct: float
    max_drawdown_pct: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
