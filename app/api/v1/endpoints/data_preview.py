from fastapi import APIRouter
from app.schemas.data_schema import DataPreviewResponse
from app.services.data.data_loader_service import DataLoaderService

router = APIRouter(prefix="/data", tags=["data"])

@router.get("/preview-sample", response_model=DataPreviewResponse)
def preview_sample():
    return DataLoaderService().preview_sample()

@router.get("/preview/{file_name}", response_model=DataPreviewResponse)
def preview_file(file_name: str):
    return DataLoaderService().preview_uploaded(file_name)
