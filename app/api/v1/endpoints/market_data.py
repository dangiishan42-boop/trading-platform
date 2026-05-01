from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.services.market_data.fno_live_data_service import get_fno_live_data_service

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.post("/fno-live-refresh")
def fno_live_refresh(session: Session = Depends(get_session)):
    return get_fno_live_data_service().refresh(session)


@router.get("/fno-live-status")
def fno_live_status(session: Session = Depends(get_session)):
    return get_fno_live_data_service().status(session)


@router.get("/fno-quotes")
def fno_quotes(
    session: Session = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=80),
    sort_by: str = Query(default="symbol"),
    sort_direction: str = Query(default="asc", pattern="^(asc|desc)$"),
):
    return get_fno_live_data_service().cached_quotes(
        session,
        limit=limit,
        offset=offset,
        search=search,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
