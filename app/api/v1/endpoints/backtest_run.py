import logging
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session
from app.api.dependencies import get_session
from app.core.logger import get_logger, log_event
from app.database.repositories.backtest_repository import BacktestRepository
from app.database.repositories.result_repository import ResultRepository
from app.models.backtest_model import BacktestRun
from app.models.result_model import BacktestResultRecord
from app.schemas.backtest_schema import BacktestRunRequest, BacktestRunResponse
from app.services.backtesting.runner import BacktestRunner

router = APIRouter(prefix="/backtest", tags=["backtest"])
logger = get_logger(__name__)

@router.post("/run", response_model=BacktestRunResponse)
def run_backtest(
    payload: BacktestRunRequest,
    request: Request,
    session: Session = Depends(get_session),
):
    run_id = uuid4().hex[:12]
    request_id = getattr(request.state, "request_id", None)
    started_at = perf_counter()

    log_event(
        logger,
        logging.INFO,
        "backtest_run_started",
        run_id=run_id,
        request_id=request_id,
        source=payload.source,
        strategy_name=payload.strategy_name,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
    )

    try:
        result = BacktestRunner().run(payload)
        BacktestRepository().create(
            session,
            BacktestRun(
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                strategy_name=result["strategy_name"],
                initial_capital=payload.initial_capital,
                commission_pct=payload.commission_pct,
                slippage_pct=payload.slippage_pct,
                total_return_pct=result["metrics"]["total_return_pct"],
                win_rate_pct=result["metrics"]["win_rate_pct"],
                max_drawdown_pct=result["metrics"]["max_drawdown_pct"],
            ),
        )
        ResultRepository().create(
            session,
            BacktestResultRecord(
                strategy_name=result["strategy_name"],
                symbol=payload.symbol,
                total_return_pct=result["metrics"]["total_return_pct"],
                win_rate_pct=result["metrics"]["win_rate_pct"],
                max_drawdown_pct=result["metrics"]["max_drawdown_pct"],
            ),
        )

        log_event(
            logger,
            logging.INFO,
            "backtest_run_completed",
            run_id=run_id,
            request_id=request_id,
            strategy_name=result["strategy_name"],
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            total_return_pct=result["metrics"]["total_return_pct"],
            win_rate_pct=result["metrics"]["win_rate_pct"],
            max_drawdown_pct=result["metrics"]["max_drawdown_pct"],
            total_trades=result["metrics"]["total_trades"],
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        return result
    except Exception:
        logger.exception(
            "backtest_run_failed",
            extra={
                "event_name": "backtest_run_failed",
                "event_fields": {
                    "run_id": run_id,
                    "request_id": request_id,
                    "strategy_name": payload.strategy_name,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                },
            },
        )
        raise
