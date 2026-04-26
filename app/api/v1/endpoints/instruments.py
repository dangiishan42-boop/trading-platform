from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.schemas.instrument_schema import (
    FnoContractsResponse,
    FnoExpiriesResponse,
    FnoUnderlyingEntry,
    InstrumentEntry,
    InstrumentSearchResponse,
    InstrumentSyncRequest,
    InstrumentSyncResponse,
)
from app.services.data.instrument_master_service import DEFAULT_ANGEL_SCRIP_MASTER_URL, InstrumentMasterService
from app.services.market_data.engine import get_market_data_engine

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.post("/sync", response_model=InstrumentSyncResponse)
def sync_instruments(payload: InstrumentSyncRequest | None = None, session: Session = Depends(get_session)):
    source_url = payload.source_url if payload and payload.source_url else DEFAULT_ANGEL_SCRIP_MASTER_URL
    imported_count = InstrumentMasterService().sync(session, source_url)
    return InstrumentSyncResponse(
        message="Instrument master synced successfully",
        imported_count=imported_count,
        source_url=source_url,
    )


@router.get("/search", response_model=InstrumentSearchResponse)
def search_instruments(
    q: str = Query(min_length=1, max_length=80),
    exchange: str | None = Query(default=None, max_length=20),
    type: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=20, ge=1, le=50),
    session: Session = Depends(get_session),
):
    payload = get_market_data_engine().search_instruments(q, exchange=exchange, session=session, instrument_type=type)
    items = payload["items"][:limit]
    return InstrumentSearchResponse(items=[InstrumentEntry.model_validate(item) for item in items])


@router.get("/fno-underlyings", response_model=list[FnoUnderlyingEntry])
def fno_underlyings(
    q: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=500, ge=1, le=1000),
    session: Session = Depends(get_session),
):
    return InstrumentMasterService().fno_underlyings(session, q=q, limit=limit)


@router.get("/fno-contracts", response_model=FnoContractsResponse)
def fno_contracts(symbol: str = Query(min_length=1, max_length=80), session: Session = Depends(get_session)):
    contracts = InstrumentMasterService().fno_contracts(session, symbol)
    return FnoContractsResponse(
        symbol=symbol.strip().upper(),
        futures=[InstrumentEntry.model_validate(row) for row in contracts["futures"]],
        options=[InstrumentEntry.model_validate(row) for row in contracts["options"]],
    )


@router.get("/fno-expiries", response_model=FnoExpiriesResponse)
def fno_expiries(symbol: str = Query(min_length=1, max_length=80), session: Session = Depends(get_session)):
    return FnoExpiriesResponse(
        symbol=symbol.strip().upper(),
        expiries=InstrumentMasterService().fno_expiries(session, symbol),
    )


@router.get("/{token}", response_model=InstrumentEntry)
def get_instrument(token: str, session: Session = Depends(get_session)):
    item = InstrumentMasterService().get_by_token(session, token)
    if item is None:
        raise HTTPException(status_code=404, detail="Instrument token not found")
    return item
