from fastapi import APIRouter

from app.schemas.data_schema import HistoricalDataRequest, HistoricalDataResponse
from app.services.data.historical_data_service import HistoricalDataService

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/historical", response_model=HistoricalDataResponse)
def fetch_historical_data(payload: HistoricalDataRequest):
    return HistoricalDataService().fetch(payload)
