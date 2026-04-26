import json

from fastapi import APIRouter
from fastapi import Depends, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.database.repositories.algo_strategy_repository import AlgoStrategyRepository
from app.models.algo_strategy_model import SavedAlgoStrategy
from app.schemas.algo_schema import (
    AlgoCapabilitiesResponse,
    AlgoSimulationRequest,
    AlgoSimulationResponse,
    AlgoValidationRequest,
    AlgoValidationResponse,
    SaveAlgoStrategyRequest,
    SavedAlgoStrategyEntry,
)
from app.services.algo.rule_simulation_service import AlgoRuleSimulationService

router = APIRouter(prefix="/algo", tags=["algo"])


@router.get("/capabilities", response_model=AlgoCapabilitiesResponse)
def capabilities():
    return {
        "data_universes": ["Single Symbol", "F&O Stocks", "Watchlist"],
        "condition_sources": ["Price", "Open", "High", "Low", "Volume", "RSI", "EMA", "SMA", "MACD", "VWAP", "ATR"],
        "operators": [">", "<", ">=", "<=", "crosses above", "crosses below"],
        "logical_connectors": ["AND", "OR"],
        "signal_types": ["buy", "sell", "exit"],
        "timeframes": ["Intraday", "Daily", "Weekly", "Monthly"],
        "entry_actions": ["Buy", "Sell", "Long", "Short"],
        "sizing_modes": ["capital_pct", "quantity", "fixed_quantity", "risk_pct"],
        "stop_types": ["none", "fixed_pct", "atr", "trailing_pct"],
        "target_types": ["none", "fixed_pct", "multi_target"],
        "max_rule_rows": 50,
        "live_execution_enabled": False,
    }


@router.post("/simulate", response_model=AlgoSimulationResponse)
def simulate(payload: AlgoSimulationRequest):
    return AlgoRuleSimulationService().simulate(payload)


@router.post("/validate", response_model=AlgoValidationResponse)
def validate_strategy(payload: AlgoValidationRequest):
    try:
        simulation_payload = AlgoSimulationRequest.model_validate(payload.config)
    except Exception as exc:
        return {"valid": False, "warnings": [], "errors": [str(exc)]}
    warnings = AlgoRuleSimulationService().validate_payload(simulation_payload)
    return {"valid": not warnings, "warnings": warnings, "errors": []}


def _serialize_strategy(row: SavedAlgoStrategy) -> SavedAlgoStrategyEntry:
    try:
        config = json.loads(row.config_json or "{}")
    except json.JSONDecodeError:
        config = {}
    return SavedAlgoStrategyEntry(
        id=row.id or 0,
        name=row.name,
        symbol=row.symbol,
        exchange=row.exchange,
        timeframe=row.timeframe,
        config=config,
        created_at=row.created_at.isoformat(),
    )


@router.get("/strategies", response_model=list[SavedAlgoStrategyEntry])
def saved_algo_strategies(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
):
    return [_serialize_strategy(row) for row in AlgoStrategyRepository().list_recent(session, limit=limit)]


@router.post("/strategies", response_model=SavedAlgoStrategyEntry)
def save_algo_strategy(payload: SaveAlgoStrategyRequest, session: Session = Depends(get_session)):
    config = payload.config or {}
    row = SavedAlgoStrategy(
        name=payload.name.strip(),
        symbol=str(config.get("symbol") or "DEMO").upper(),
        exchange=str(config.get("exchange") or "NSE").upper(),
        timeframe=str(config.get("timeframe") or "1D").upper(),
        config_json=json.dumps(config, sort_keys=True),
    )
    return _serialize_strategy(AlgoStrategyRepository().create(session, row))
