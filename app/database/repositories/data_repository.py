from pathlib import Path
from sqlmodel import Session, select

from app.models.dataset_model import UploadedDataset

class DataRepository:
    def list_csv_files(self, directory: Path) -> list[str]:
        return sorted([p.name for p in directory.glob("*.csv")])

    def list_recent_datasets(self, session: Session, limit: int = 10) -> list[UploadedDataset]:
        statement = (
            select(UploadedDataset)
            .order_by(UploadedDataset.uploaded_at.desc(), UploadedDataset.id.desc())
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def create_dataset(self, session: Session, dataset: UploadedDataset) -> UploadedDataset:
        session.add(dataset)
        session.commit()
        session.refresh(dataset)
        return dataset
