from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstrumentEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exchange: str
    symbol: str
    name: str
    token: str
    instrument_type: str = ""
    lot_size: int | None = None
    tick_size: float | None = None


class InstrumentSyncResponse(BaseModel):
    message: str
    imported_count: int = Field(ge=0)
    source_url: str


class InstrumentSearchResponse(BaseModel):
    items: list[InstrumentEntry]


class InstrumentSyncRequest(BaseModel):
    source_url: str | None = Field(default=None, max_length=500)

    @field_validator("source_url")
    @classmethod
    def normalize_source_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
