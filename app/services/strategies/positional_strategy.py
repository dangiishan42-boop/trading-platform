from app.services.strategies.ema_crossover_strategy import EMACrossoverStrategy

class PositionalStrategy(EMACrossoverStrategy):
    slug = "positional"
    name = "Positional"
    description = "Positional preset built on the EMA crossover framework."
