from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_session
from app.schemas.screener_schema import (
    ScreenerCapabilitiesResponse,
    ScreenerRunRequest,
    ScreenerRunResponse,
    ScreenerSavedScreenCreate,
)
from app.services.screener.screener_service import ScreenerService

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("/capabilities", response_model=ScreenerCapabilitiesResponse)
def capabilities():
    return ScreenerService().capabilities()


@router.post("/run", response_model=ScreenerRunResponse)
def run_screener(payload: ScreenerRunRequest, session: Session = Depends(get_session)):
    return ScreenerService().run(payload, session=session)


@router.get("/saved")
def saved_screens():
    return ScreenerService().list_saved_screens()


@router.post("/saved")
def save_screen(payload: ScreenerSavedScreenCreate):
    return ScreenerService().save_screen(payload)


@router.delete("/saved/{screen_id}")
def delete_screen(screen_id: str):
    return ScreenerService().delete_screen(screen_id)
