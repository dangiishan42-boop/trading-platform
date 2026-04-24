from fastapi import APIRouter

from app.schemas.strategy_scorecard_schema import StrategyScorecardRequest, StrategyScorecardResponse
from app.services.analytics.strategy_scorecard_service import StrategyScorecardService

router = APIRouter(prefix="/strategy-scorecard", tags=["strategy-scorecard"])


@router.post("/run", response_model=StrategyScorecardResponse)
def run_strategy_scorecard(payload: StrategyScorecardRequest):
    return StrategyScorecardService().calculate(
        initial_capital=payload.initial_capital,
        equity_curve=payload.equity_curve,
        trades=payload.trades,
    )
