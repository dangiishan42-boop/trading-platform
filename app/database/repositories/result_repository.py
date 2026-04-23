from sqlmodel import Session, select
from app.models.result_model import BacktestResultRecord

class ResultRepository:
    def list_all(self, session: Session) -> list[BacktestResultRecord]:
        return list(session.exec(select(BacktestResultRecord).order_by(BacktestResultRecord.id.desc())).all())

    def create(self, session: Session, row: BacktestResultRecord) -> BacktestResultRecord:
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
