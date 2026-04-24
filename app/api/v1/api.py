from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, dashboard, data_upload, data_preview, indicators, strategies,
    strategy_builder, backtest_run, backtest_history, results, reports,
    charts, portfolio, watchlist, risk, optimization, monte_carlo, market_regime, strategy_scorecard, market_watch, settings, users,
    historical_data, algo
)

router = APIRouter()
for child in [
    auth.router, dashboard.router, data_upload.router, data_preview.router,
    indicators.router, strategies.router, strategy_builder.router,
    backtest_run.router, backtest_history.router, results.router,
    reports.router, charts.router, portfolio.router, watchlist.router,
    risk.router, optimization.router, monte_carlo.router, market_regime.router, strategy_scorecard.router, market_watch.router, settings.router, users.router,
    historical_data.router, algo.router
]:
    router.include_router(child)
