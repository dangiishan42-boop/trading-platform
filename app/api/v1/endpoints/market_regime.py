from fastapi import APIRouter

from app.schemas.market_regime_schema import MarketRegimeRunRequest, MarketRegimeRunResponse
from app.services.analytics.market_regime_analysis import MarketRegimeAnalysis

router = APIRouter(prefix="/market-regime", tags=["market-regime"])


@router.post("/run", response_model=MarketRegimeRunResponse)
def run_market_regime_analysis(payload: MarketRegimeRunRequest):
    return MarketRegimeAnalysis().run(
        market_data=payload.market_data,
        trades=payload.trades,
        initial_capital=payload.initial_capital,
        slope_threshold_pct=payload.slope_threshold_pct,
    )
