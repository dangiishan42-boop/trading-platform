from sqlmodel import Session, select
from app.models.backtest_model import BacktestRun

class BacktestRepository:
    def list_all(self, session: Session) -> list[BacktestRun]:
        return list(session.exec(select(BacktestRun).order_by(BacktestRun.id.desc())).all())

    def list_recent(self, session: Session, limit: int = 10) -> list[BacktestRun]:
        statement = (
            select(BacktestRun)
            .order_by(BacktestRun.created_at.desc(), BacktestRun.id.desc())
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def create(self, session: Session, run: BacktestRun) -> BacktestRun:
        session.add(run)
        session.commit()
        session.refresh(run)
        return run
