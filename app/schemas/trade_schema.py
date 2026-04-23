from pydantic import BaseModel

class TradeSchema(BaseModel):
    entry_time: str
    exit_time: str
    pnl: float
