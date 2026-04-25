from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class InstrumentMaster(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("exchange", "token", name="uq_instrument_exchange_token"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    exchange: str = Field(index=True, max_length=20)
    symbol: str = Field(index=True, max_length=80)
    name: str = Field(index=True, max_length=200)
    token: str = Field(index=True, max_length=64)
    instrument_type: str = Field(default="", max_length=64)
    lot_size: int | None = None
    tick_size: float | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
