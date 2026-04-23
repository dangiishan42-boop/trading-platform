from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class BacktestRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str
    timeframe: str
    strategy_name: str
    initial_capital: float
    commission_pct: float
    slippage_pct: float = 0.0
    total_return_pct: float = 0.0
    win_rate_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
