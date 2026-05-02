from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.services.data.stocks_service import StocksService

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("")
def list_stocks(
    universe: str = Query(default="fno", pattern="^(fno|all|nse|bse|nifty50|nifty_50)$"),
    exchange: str = Query(default="ALL", pattern="^(NSE|BSE|ALL)$"),
    search: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="symbol", pattern="^(symbol|percent_change|volume|market_cap|pe|eps)$"),
    sort_direction: str = Query(default="asc", pattern="^(asc|desc)$"),
    session: Session = Depends(get_session),
):
    return StocksService().list_stocks(
        session,
        universe=universe,
        exchange=exchange,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
