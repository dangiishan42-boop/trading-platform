from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.api.dependencies import get_session
from app.database.repositories.backtest_repository import BacktestRepository
from app.schemas.backtest_schema import BacktestHistoryEntry

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.get("/history", response_model=list[BacktestHistoryEntry])
def history(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    return BacktestRepository().list_recent(session, limit=limit)
