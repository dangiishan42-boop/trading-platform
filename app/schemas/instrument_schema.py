from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstrumentEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exchange: str
    symbol: str
    name: str
    token: str
    trading_symbol: str | None = None
    instrument_type: str = ""
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None
    lot_size: int | None = None
    tick_size: float | None = None
    underlying: str | None = None
    is_equity: bool = False
    is_fno: bool = False
    is_future: bool = False
    is_option: bool = False


class InstrumentSyncResponse(BaseModel):
    message: str
    imported_count: int = Field(ge=0)
    source_url: str


class InstrumentSearchResponse(BaseModel):
    items: list[InstrumentEntry]


class FnoUnderlyingEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str
    exchange: str = "NSE"
    equity_token: str | None = None
    nearest_future_token: str | None = None
    active_expiries: str = ""
    has_futures: bool = False
    has_options: bool = False
    lot_size: int | None = None


class FnoContractsResponse(BaseModel):
    symbol: str
    futures: list[InstrumentEntry]
    options: list[InstrumentEntry]


class FnoExpiriesResponse(BaseModel):
    symbol: str
    expiries: list[str]


class InstrumentSyncRequest(BaseModel):
    source_url: str | None = Field(default=None, max_length=500)

    @field_validator("source_url")
    @classmethod
    def normalize_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
