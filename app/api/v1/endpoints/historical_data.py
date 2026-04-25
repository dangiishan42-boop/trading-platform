from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_session
from app.schemas.data_schema import HistoricalDataRequest, HistoricalDataResponse
from app.services.data.historical_data_service import HistoricalDataService

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/historical", response_model=HistoricalDataResponse)
def fetch_historical_data(payload: HistoricalDataRequest, session: Session = Depends(get_session)):
    return HistoricalDataService().fetch(payload, session=session)
