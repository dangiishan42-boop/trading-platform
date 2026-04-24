from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_session
from app.api.v1.endpoints.data_upload import _store_dataset_metadata
from app.schemas.data_schema import AngelDataFetchRequest
from app.schemas.market_watch_schema import (
    MarketWatchBacktestDatasetResponse,
    MarketWatchCandleRequest,
    MarketWatchCandleResponse,
    MarketWatchIndexResponse,
    MarketWatchQuoteResponse,
    MarketWatchSymbolRequest,
)
from app.services.data.angel_smartapi_service import AngelSmartApiService
from app.services.data.market_watch_service import MarketWatchService

router = APIRouter(prefix="/market-watch", tags=["market-watch"])


@router.post("/quote", response_model=MarketWatchQuoteResponse)
def quote(payload: MarketWatchSymbolRequest):
    return MarketWatchService().quote(payload.query, payload.exchange, payload.symbol_token)


@router.post("/candles", response_model=MarketWatchCandleResponse)
def candles(payload: MarketWatchCandleRequest):
    return MarketWatchService().candles(
        payload.query,
        payload.exchange,
        payload.symbol_token,
        payload.interval,
        payload.fromdate,
        payload.todate,
    )


@router.get("/indices", response_model=list[MarketWatchIndexResponse])
def indices():
    return MarketWatchService().indices()


@router.post("/use-for-backtest", response_model=MarketWatchBacktestDatasetResponse)
def use_for_backtest(payload: MarketWatchCandleRequest, session: Session = Depends(get_session)):
    service = MarketWatchService()
    resolved = service.resolve_symbol(payload.query, payload.exchange, payload.symbol_token)
    candle_request = service._candle_request(resolved, payload.interval, payload.fromdate, payload.todate)
    fetched = AngelSmartApiService().fetch_dataset(
        AngelDataFetchRequest(
            exchange=candle_request.exchange,
            symbol_token=candle_request.symbol_token,
            interval=candle_request.interval,
            fromdate=candle_request.fromdate,
            todate=candle_request.todate,
        )
    )
    _store_dataset_metadata(session, fetched)
    return MarketWatchBacktestDatasetResponse(
        message="Market watch candles saved for backtesting",
        symbol=resolved.symbol,
        stock_name=resolved.stock_name,
        exchange=resolved.exchange,
        symbol_token=resolved.symbol_token,
        stored_file_name=fetched.file_name,
        row_count=fetched.preview.total_rows,
        min_date=fetched.preview.min_date,
        max_date=fetched.preview.max_date,
    )
