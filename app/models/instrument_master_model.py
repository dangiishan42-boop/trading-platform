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
    trading_symbol: str | None = Field(default=None, index=True, max_length=120)
    instrument_type: str = Field(default="", max_length=64)
    expiry: str | None = Field(default=None, index=True, max_length=32)
    strike: float | None = None
    option_type: str | None = Field(default=None, max_length=8)
    lot_size: int | None = None
    tick_size: float | None = None
    underlying: str | None = Field(default=None, index=True, max_length=80)
    is_equity: bool = Field(default=False, index=True)
    is_fno: bool = Field(default=False, index=True)
    is_future: bool = Field(default=False, index=True)
    is_option: bool = Field(default=False, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FnoUnderlying(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("symbol", name="uq_fno_underlying_symbol"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, max_length=80)
    name: str = Field(index=True, max_length=200)
    exchange: str = Field(default="NSE", max_length=20)
    equity_token: str | None = Field(default=None, index=True, max_length=64)
    nearest_future_token: str | None = Field(default=None, index=True, max_length=64)
    active_expiries: str = Field(default="", max_length=500)
    has_futures: bool = Field(default=False, index=True)
    has_options: bool = Field(default=False, index=True)
    lot_size: int | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
