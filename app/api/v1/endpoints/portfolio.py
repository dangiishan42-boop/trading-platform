from fastapi import APIRouter

from app.schemas.portfolio_backtest_schema import (
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
)
from app.services.backtesting.portfolio_backtest_service import PortfolioBacktestService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/summary")
def portfolio_summary():
    return {"message": "Portfolio module ready"}


@router.post("/backtest", response_model=PortfolioBacktestResponse)
def run_portfolio_backtest(payload: PortfolioBacktestRequest):
    return PortfolioBacktestService().run(payload)
