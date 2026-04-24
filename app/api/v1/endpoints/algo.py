from fastapi import APIRouter

from app.schemas.algo_schema import AlgoCapabilitiesResponse, AlgoSimulationRequest, AlgoSimulationResponse
from app.services.algo.rule_simulation_service import AlgoRuleSimulationService

router = APIRouter(prefix="/algo", tags=["algo"])


@router.get("/capabilities", response_model=AlgoCapabilitiesResponse)
def capabilities():
    return {
        "condition_sources": ["Price", "EMA", "RSI", "MACD", "Volume"],
        "operators": [">", "<", ">=", "<=", "crosses above", "crosses below"],
        "logical_connectors": ["AND", "OR"],
        "signal_types": ["buy", "sell", "exit"],
        "max_rule_rows": 10,
        "live_execution_enabled": False,
    }


@router.post("/simulate", response_model=AlgoSimulationResponse)
def simulate(payload: AlgoSimulationRequest):
    return AlgoRuleSimulationService().simulate(payload)
