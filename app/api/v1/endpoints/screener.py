from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_session
from app.schemas.screener_schema import (
    ScreenerCapabilitiesResponse,
    ScreenerFormulaValidateRequest,
    ScreenerFormulaValidateResponse,
    ScreenerRunRequest,
    ScreenerRunResponse,
    ScreenerSavedScreenCreate,
)
from app.services.screener.formula_engine import validate_formula
from app.services.screener.screener_service import ScreenerService

router = APIRouter(prefix="/screener", tags=["screener"])


@router.get("/capabilities", response_model=ScreenerCapabilitiesResponse)
def capabilities():
    return ScreenerService().capabilities()


@router.post("/run", response_model=ScreenerRunResponse)
def run_screener(payload: ScreenerRunRequest, session: Session = Depends(get_session)):
    return ScreenerService().run(payload, session=session)


@router.post("/formula/validate", response_model=ScreenerFormulaValidateResponse)
def validate_screener_formula(payload: ScreenerFormulaValidateRequest):
    result = validate_formula(payload.expression)
    return {
        "valid": result.valid,
        "normalized_expression": result.normalized_expression,
        "errors": result.errors,
        "referenced_metrics": result.referenced_metrics,
    }


@router.get("/saved")
def saved_screens():
    return ScreenerService().list_saved_screens()


@router.post("/saved")
def save_screen(payload: ScreenerSavedScreenCreate):
    return ScreenerService().save_screen(payload)


@router.delete("/saved/{screen_id}")
def delete_screen(screen_id: str):
    return ScreenerService().delete_screen(screen_id)
