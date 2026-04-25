from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WatchlistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return str(value or "").strip()


class WatchlistUpdateRequest(WatchlistCreateRequest):
    pass


class WatchlistItemCreateRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=80)
    exchange: str = Field(default="NSE", min_length=1, max_length=20)
    token: str | None = Field(default=None, max_length=64)
    display_name: str | None = Field(default=None, max_length=200)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value):
        return str(value or "").strip().upper().replace(" ", "")

    @field_validator("exchange", mode="before")
    @classmethod
    def normalize_exchange(cls, value):
        return str(value or "NSE").strip().upper()

    @field_validator("token", "display_name", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class WatchlistItemResponse(BaseModel):
    id: int
    watchlist_id: int
    symbol: str
    exchange: str
    token: str | None = None
    display_name: str | None = None
    created_at: datetime


class WatchlistResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    items: list[WatchlistItemResponse] = []
