from pydantic import BaseModel

class ResultSummary(BaseModel):
    strategy_name: str
    symbol: str
    total_return_pct: float
    win_rate_pct: float
    max_drawdown_pct: float
