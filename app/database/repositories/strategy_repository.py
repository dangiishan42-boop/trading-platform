from sqlmodel import Session, select
from app.models.strategy_model import SavedStrategy
from app.models.strategy_config_model import SavedStrategyConfiguration

class StrategyRepository:
    def list_all(self, session: Session) -> list[SavedStrategy]:
        return list(session.exec(select(SavedStrategy)).all())

    def list_recent_configurations(
        self,
        session: Session,
        limit: int = 10,
    ) -> list[SavedStrategyConfiguration]:
        statement = (
            select(SavedStrategyConfiguration)
            .order_by(SavedStrategyConfiguration.created_at.desc(), SavedStrategyConfiguration.id.desc())
            .limit(limit)
        )
        return list(session.exec(statement).all())

    def create(self, session: Session, strategy: SavedStrategy) -> SavedStrategy:
        session.add(strategy)
        session.commit()
        session.refresh(strategy)
        return strategy

    def create_configuration(
        self,
        session: Session,
        configuration: SavedStrategyConfiguration,
    ) -> SavedStrategyConfiguration:
        session.add(configuration)
        session.commit()
        session.refresh(configuration)
        return configuration
