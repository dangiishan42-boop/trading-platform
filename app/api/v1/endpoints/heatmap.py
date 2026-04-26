from fastapi import APIRouter, HTTPException

from app.schemas.heatmap_schema import (
    HeatmapCapabilitiesResponse,
    HeatmapRunRequest,
    HeatmapRunResponse,
    HeatmapSectorDetailResponse,
    HeatmapSectorListItem,
    HeatmapSectorRequest,
)
from app.services.heatmap.heatmap_service import HeatmapService

router = APIRouter(prefix="/heatmap", tags=["heatmap"])


@router.get("/capabilities", response_model=HeatmapCapabilitiesResponse)
def capabilities():
    return HeatmapService().capabilities()


@router.post("/run", response_model=HeatmapRunResponse)
def run_heatmap(payload: HeatmapRunRequest):
    return HeatmapService().run(payload)


@router.get("/sectors", response_model=list[HeatmapSectorListItem])
def sectors():
    return HeatmapService().sectors()


@router.post("/sector/{sector_slug}", response_model=HeatmapSectorDetailResponse)
def sector_detail(sector_slug: str, payload: HeatmapSectorRequest):
    response = HeatmapService().sector_detail(sector_slug, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Sector not found")
    return response
