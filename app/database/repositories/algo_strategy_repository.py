from sqlmodel import Session, select

from app.models.algo_strategy_model import SavedAlgoStrategy


class AlgoStrategyRepository:
    def list_recent(self, session: Session, limit: int = 50) -> list[SavedAlgoStrategy]:
        statement = (
            select(SavedAlgoStrategy)
            .order_by(SavedAlgoStrategy.created_at.desc(), SavedAlgoStrategy.id.desc())
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def create(self, session: Session, strategy: SavedAlgoStrategy) -> SavedAlgoStrategy:
        session.add(strategy)
        session.commit()
        session.refresh(strategy)
        return strategy
