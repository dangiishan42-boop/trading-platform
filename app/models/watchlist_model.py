from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Watchlist(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("name", name="uq_watchlist_name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WatchlistItem(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("watchlist_id", "symbol", "exchange", name="uq_watchlist_item_symbol_exchange"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    watchlist_id: int = Field(foreign_key="watchlist.id", index=True)
    symbol: str = Field(index=True, max_length=80)
    exchange: str = Field(default="NSE", index=True, max_length=20)
    token: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
