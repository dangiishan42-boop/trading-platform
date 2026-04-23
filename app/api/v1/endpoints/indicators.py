from fastapi import APIRouter
from app.services.indicators import registry as indicator_registry

router = APIRouter(prefix="/indicators", tags=["indicators"])

@router.get("/available")
def available_indicators():
    return indicator_registry.available_indicators()
