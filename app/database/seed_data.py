import json

from sqlmodel import Session, select

from app.database.session import engine
from app.models.strategy_model import SavedStrategy


def seed_builtin_strategies() -> None:
    presets = [
        ("EMA Crossover", "ema_crossover", {"fast_period": 20, "slow_period": 50}),
        ("RSI Reversal", "rsi_reversal", {"rsi_period": 14, "oversold": 30, "overbought": 70}),
    ]
    with Session(engine) as session:
        for name, slug, params in presets:
            exists = session.exec(select(SavedStrategy).where(SavedStrategy.slug == slug)).first()
            if not exists:
                session.add(
                    SavedStrategy(
                        name=name,
                        slug=slug,
                        description=name,
                        parameters_json=json.dumps(params, sort_keys=True),
                    )
                )
        session.commit()
