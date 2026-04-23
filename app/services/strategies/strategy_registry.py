from app.core.exceptions import StrategyNotFoundError
from app.services.strategies.base_strategy import BaseStrategy
from app.services.strategies.breakout_strategy import BreakoutStrategy
from app.services.strategies.ema_crossover_strategy import EMACrossoverStrategy
from app.services.strategies.intraday_strategy import IntradayStrategy
from app.services.strategies.mean_reversion_strategy import MeanReversionStrategy
from app.services.strategies.positional_strategy import PositionalStrategy
from app.services.strategies.rsi_reversal_strategy import RSIReversalStrategy
from app.services.strategies.trend_following_strategy import TrendFollowingStrategy

class StrategyRegistry:
    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}
        self._lookup: dict[str, str] = {}
        for strategy in [
            EMACrossoverStrategy(),
            RSIReversalStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            MeanReversionStrategy(),
            IntradayStrategy(),
            PositionalStrategy(),
        ]:
            self.register(strategy)

    def _normalize_identifier(self, value: str) -> str:
        return " ".join(value.replace("_", " ").replace("-", " ").split()).casefold()

    def register(self, strategy: BaseStrategy) -> None:
        self._strategies[strategy.slug] = strategy
        for identifier in strategy.identifiers():
            normalized = self._normalize_identifier(identifier)
            existing_slug = self._lookup.get(normalized)
            if existing_slug and existing_slug != strategy.slug:
                raise ValueError(
                    f"Strategy identifier '{identifier}' is already registered to '{existing_slug}'"
                )
            self._lookup[normalized] = strategy.slug

    def get(self, identifier: str) -> BaseStrategy:
        normalized_identifier = self._normalize_identifier(identifier)
        slug = self._lookup.get(normalized_identifier)
        if not slug:
            raise StrategyNotFoundError(f"Strategy not found: {identifier}")
        strategy = self._strategies[slug]
        return strategy

    def available(self) -> list[dict]:
        return [strategy.definition().model_dump(mode="json") for strategy in self._strategies.values()]
