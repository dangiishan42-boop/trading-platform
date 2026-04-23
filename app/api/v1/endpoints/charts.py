from fastapi import APIRouter
from app.services.analytics.chart_service import ChartService
from app.services.data.data_loader_service import DataLoaderService

router = APIRouter(prefix="/charts", tags=["charts"])

@router.get("/sample-close")
def sample_close_chart():
    frame = DataLoaderService().load_sample()
    html = ChartService().price_chart(frame, "Sample Close Chart")
    return {"chart_html": html}
