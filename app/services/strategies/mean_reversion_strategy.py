from app.services.strategies.rsi_reversal_strategy import RSIReversalStrategy

class MeanReversionStrategy(RSIReversalStrategy):
    slug = "mean_reversion"
    name = "Mean Reversion"
    description = "Mean-reversion preset built on the RSI reversal framework."
