from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlmodel import Session

from app.api.dependencies import get_session
from app.database.repositories.data_repository import DataRepository
from app.models.dataset_model import UploadedDataset
from app.schemas.data_schema import DataUploadResponse, UploadedDatasetEntry
from app.services.data.data_loader_service import DataLoaderService

router = APIRouter(prefix="/data", tags=["data"])


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@router.post("/upload", response_model=DataUploadResponse)
async def upload_data(file: UploadFile = File(...), session: Session = Depends(get_session)):
    try:
        content = await file.read()
    finally:
        await file.close()

    payload = DataLoaderService().save_upload(file.filename, content, file.content_type)
    DataRepository().create_dataset(
        session,
        UploadedDataset(
            original_file_name=payload.original_file_name,
            stored_file_name=payload.file_name,
            row_count=payload.preview.total_rows,
            min_date=_parse_optional_datetime(payload.preview.min_date),
            max_date=_parse_optional_datetime(payload.preview.max_date),
        ),
    )
    return payload


@router.get("/uploads", response_model=list[UploadedDatasetEntry])
def list_uploaded_datasets(
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    return DataRepository().list_recent_datasets(session, limit=limit)
