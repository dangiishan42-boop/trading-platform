from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from app.api.dependencies import get_session
from app.database.repositories.result_repository import ResultRepository
from app.schemas.backtest_schema import BacktestExportRequest
from app.services.analytics.result_export_service import ResultExportService

router = APIRouter(prefix="/results", tags=["results"])

@router.get("")
def list_results(session: Session = Depends(get_session)):
    return ResultRepository().list_all(session)


@router.post("/export-csv")
def export_latest_result_csv(payload: BacktestExportRequest):
    export_service = ResultExportService()
    csv_content = export_service.build_csv(payload)
    filename = export_service.build_filename(payload)
    return StreamingResponse(
        BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
