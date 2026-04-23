from fastapi import APIRouter
from pydantic import Field

from app.schemas.backtest_schema import BacktestRunRequest
from app.services.optimization.parameter_optimizer import ParameterOptimizer

router = APIRouter(prefix="/optimization", tags=["optimization"])


class OptimizationRunRequest(BacktestRunRequest):
    max_results: int = Field(default=20, ge=1, le=50)


@router.get("/capabilities")
def capabilities():
    return {"supported": ["grid_search", "walk_forward", "monte_carlo"]}


@router.post("/run")
def run_optimization(payload: OptimizationRunRequest):
    return ParameterOptimizer().optimize(payload, max_results=payload.max_results)
