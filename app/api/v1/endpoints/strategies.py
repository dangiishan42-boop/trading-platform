import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session
from app.api.dependencies import get_session
from app.core.exceptions import InvalidRequestError, ResourceConflictError
from app.database.repositories.strategy_repository import StrategyRepository
from app.models.strategy_config_model import SavedStrategyConfiguration
from app.models.strategy_model import SavedStrategy
from app.schemas.strategy_schema import (
    SaveStrategyConfigurationRequest,
    SaveStrategyRequest,
    SavedStrategyConfigurationEntry,
)
from app.services.strategies.strategy_registry import StrategyRegistry

router = APIRouter(prefix="/strategies", tags=["strategies"])

@router.get("/available")
def available_strategies():
    return StrategyRegistry().available()

@router.get("/saved")
def saved_strategies(session: Session = Depends(get_session)):
    return StrategyRepository().list_all(session)


@router.get("/configurations", response_model=list[SavedStrategyConfigurationEntry])
def saved_strategy_configurations(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    return StrategyRepository().list_recent_configurations(session, limit=limit)

@router.post("/save")
def save_strategy(payload: SaveStrategyRequest, session: Session = Depends(get_session)):
    row = SavedStrategy(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        parameters_json=json.dumps(payload.parameters, sort_keys=True),
    )
    try:
        return StrategyRepository().create(session, row)
    except IntegrityError as exc:
        session.rollback()
        raise ResourceConflictError(f"Strategy slug already exists: {payload.slug}") from exc


@router.post("/configurations", response_model=SavedStrategyConfigurationEntry)
def save_strategy_configuration(
    payload: SaveStrategyConfigurationRequest,
    session: Session = Depends(get_session),
):
    display_name = payload.display_name.strip()
    if not display_name:
        raise InvalidRequestError("display_name is required")

    strategy = StrategyRegistry().get(payload.strategy_name)
    validated_parameters = strategy.validate_parameters(payload.parameters).model_dump(mode="json")

    configuration = SavedStrategyConfiguration(
        strategy_name=strategy.slug,
        display_name=display_name,
        parameters_json=json.dumps(validated_parameters, sort_keys=True),
    )
    return StrategyRepository().create_configuration(session, configuration)
