from app.services.strategies.ema_crossover_strategy import EMACrossoverStrategy

class TrendFollowingStrategy(EMACrossoverStrategy):
    slug = "trend_following"
    name = "Trend Following"
    description = "Trend-following preset built on the EMA crossover framework."
