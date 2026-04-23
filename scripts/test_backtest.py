from app.services.backtesting.runner import BacktestRunner
from app.schemas.backtest_schema import BacktestRunRequest
print(BacktestRunner().run(BacktestRunRequest(strategy_name="ema_crossover")))
