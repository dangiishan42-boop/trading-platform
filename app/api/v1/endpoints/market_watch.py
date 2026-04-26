from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_session
from app.api.v1.endpoints.data_upload import _store_dataset_metadata
from app.schemas.market_watch_schema import (
    MarketWatchBacktestDatasetResponse,
    MarketWatchCandleRequest,
    MarketWatchCandleResponse,
    MarketWatchIndexResponse,
    MarketWatchQuoteResponse,
    MarketWatchSymbolRequest,
)
from app.services.data.data_loader_service import DataLoaderService
from app.services.data.market_watch_service import MarketWatchService

router = APIRouter(prefix="/market-watch", tags=["market-watch"])


@router.post("/quote", response_model=MarketWatchQuoteResponse)
def quote(payload: MarketWatchSymbolRequest, session: Session = Depends(get_session)):
    service = MarketWatchService()
    try:
        return service.quote(payload.query, payload.exchange, payload.symbol_token, session=session)
    except TypeError:
        return service.quote(payload.query, payload.exchange, payload.symbol_token)


@router.post("/candles", response_model=MarketWatchCandleResponse)
def candles(payload: MarketWatchCandleRequest, session: Session = Depends(get_session)):
    service = MarketWatchService()
    try:
        return service.candles(
            payload.query,
            payload.exchange,
            payload.symbol_token,
            payload.interval,
            payload.fromdate,
            payload.todate,
            session=session,
        )
    except TypeError:
        return service.candles(
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


@router.get("/detail/{symbol}/fundamentals")
def detail_fundamentals(symbol: str):
    return MarketWatchService().fundamentals_placeholder(symbol)


@router.get("/detail/{symbol}/option-chain")
def detail_option_chain(symbol: str):
    return MarketWatchService().option_chain_placeholder(symbol)


@router.get("/detail/{symbol}/peers")
def detail_peers(symbol: str):
    return MarketWatchService().peers(symbol)


@router.get("/detail/{symbol}/technical")
def detail_technical(symbol: str, exchange: str = "NSE", symbol_token: str | None = None, session: Session = Depends(get_session)):
    return MarketWatchService().technical_detail(symbol, exchange, symbol_token, session=session)


@router.post("/use-for-backtest", response_model=MarketWatchBacktestDatasetResponse)
def use_for_backtest(payload: MarketWatchCandleRequest, session: Session = Depends(get_session)):
    service = MarketWatchService()
    resolved = service.resolve_symbol(payload.query, payload.exchange, payload.symbol_token, session=session)
    candle_data = service.candles(
        payload.query,
        payload.exchange,
        payload.symbol_token,
        payload.interval,
        payload.fromdate,
        payload.todate,
        session=session,
    )
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "Date": row["datetime"],
                "Open": row["open"],
                "High": row["high"],
                "Low": row["low"],
                "Close": row["close"],
                "Volume": row["volume"],
            }
            for row in candle_data["rows"]
        ]
    )
    fetched = DataLoaderService().save_dataframe_upload(
        f"market_watch_{resolved.exchange}_{resolved.symbol}_{payload.interval}.csv",
        frame,
        message="Market watch candles saved for backtesting",
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
