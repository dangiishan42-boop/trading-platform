from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.dependencies import get_session
from app.schemas.heatmap_schema import (
    HeatmapCapabilitiesResponse,
    HeatmapRunRequest,
    HeatmapRunResponse,
    HeatmapIndustryDetailResponse,
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
def run_heatmap(payload: HeatmapRunRequest, session: Session = Depends(get_session)):
    return HeatmapService().run(payload, session=session)


@router.get("/sectors", response_model=list[HeatmapSectorListItem])
def sectors():
    return HeatmapService().sectors()


@router.post("/sector/{sector_slug}", response_model=HeatmapSectorDetailResponse)
def sector_detail(sector_slug: str, payload: HeatmapSectorRequest):
    response = HeatmapService().sector_detail(sector_slug, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Sector not found")
    return response


@router.get("/sector/{sector_slug}", response_model=HeatmapSectorDetailResponse)
def sector_detail_get(sector_slug: str):
    response = HeatmapService().sector_detail(sector_slug, HeatmapSectorRequest())
    if response is None:
        raise HTTPException(status_code=404, detail="Sector not found")
    return response


@router.post("/sector/{sector_slug}/industry/{industry_slug}", response_model=HeatmapIndustryDetailResponse)
def industry_detail(sector_slug: str, industry_slug: str, payload: HeatmapSectorRequest):
    response = HeatmapService().industry_detail(sector_slug, industry_slug, payload)
    if response is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return response


@router.get("/sector/{sector_slug}/industry/{industry_slug}", response_model=HeatmapIndustryDetailResponse)
def industry_detail_get(sector_slug: str, industry_slug: str):
    response = HeatmapService().industry_detail(sector_slug, industry_slug, HeatmapSectorRequest())
    if response is None:
        raise HTTPException(status_code=404, detail="Industry not found")
    return response


@router.post("/rotation")
def rotation(payload: dict = {}):
    return HeatmapService().rotation(payload)


@router.post("/breadth")
def breadth(payload: dict = {}):
    return HeatmapService().breadth_dashboard(payload)


@router.post("/factors")
def factors(payload: dict = {}):
    return HeatmapService().factors(payload)


@router.post("/insights")
def insights(payload: dict = {}):
    return HeatmapService().insights(payload)
