from fastapi import APIRouter

from app.schemas.monte_carlo_schema import MonteCarloRunRequest, MonteCarloRunResponse
from app.services.optimization.monte_carlo import MonteCarloAnalysis

router = APIRouter(prefix="/monte-carlo", tags=["monte-carlo"])


@router.post("/run", response_model=MonteCarloRunResponse)
def run_monte_carlo(payload: MonteCarloRunRequest):
    return MonteCarloAnalysis().run(
        trades=payload.trades,
        initial_capital=payload.initial_capital,
        simulation_count=payload.simulation_count,
        drawdown_threshold_pct=payload.drawdown_threshold_pct,
        noise_pct=payload.noise_pct,
    )
