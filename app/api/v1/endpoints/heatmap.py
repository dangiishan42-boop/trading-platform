from fastapi import APIRouter

from app.schemas.heatmap_schema import (
    HeatmapCapabilitiesResponse,
    HeatmapRunRequest,
    HeatmapRunResponse,
)
from app.services.heatmap.heatmap_service import HeatmapService

router = APIRouter(prefix="/heatmap", tags=["heatmap"])


@router.get("/capabilities", response_model=HeatmapCapabilitiesResponse)
def capabilities():
    return HeatmapService().capabilities()


@router.post("/run", response_model=HeatmapRunResponse)
def run_heatmap(payload: HeatmapRunRequest):
    return HeatmapService().run(payload)
