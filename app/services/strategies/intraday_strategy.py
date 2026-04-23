from app.services.strategies.ema_crossover_strategy import EMACrossoverStrategy

class IntradayStrategy(EMACrossoverStrategy):
    slug = "intraday"
    name = "Intraday"
    description = "Intraday preset built on the EMA crossover framework."
