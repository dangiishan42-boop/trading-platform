from app.schemas.backtest_schema import BacktestRunRequest
from app.services.analytics.chart_service import ChartService
from app.services.analytics.metrics_service import MetricsService
from app.services.backtesting.engine import BacktestEngine
from app.services.data.date_range_filter_service import DateRangeFilterService
from app.services.data.data_loader_service import DataLoaderService
from app.services.strategies.strategy_registry import StrategyRegistry

class BacktestRunner:
    def run(self, payload: BacktestRunRequest) -> dict:
        loader = DataLoaderService()
        frame = loader.load(payload.source, payload.file_name)
        frame = DateRangeFilterService().filter(frame, payload.from_date, payload.to_date)
        strategy = StrategyRegistry().get(payload.strategy_name)
        signal_frame = strategy.apply(frame, payload.parameters)
        raw = BacktestEngine().run(
            signal_frame,
            payload.initial_capital,
            payload.commission_pct,
            payload.slippage_pct,
            payload.position_sizing_mode,
            payload.fixed_quantity,
            payload.capital_per_trade,
            payload.equity_pct_per_trade,
            payload.stop_loss_pct,
            payload.take_profit_pct,
        )
        metrics = MetricsService().calculate(payload.initial_capital, raw["ending_equity"], raw["trades"], raw["equity_curve"])
        chart_service = ChartService()
        chart_html = chart_service.equity_curve(raw["equity_curve"], strategy.name)
        drawdown_chart_html = chart_service.drawdown_curve(raw["equity_curve"], strategy.name)
        market_data = [
            {
                "timestamp": str(row["Date"]),
                "close": round(float(row["Close"]), 4),
            }
            for _, row in frame.iterrows()
        ]
        return {
            "strategy_name": strategy.slug,
            "symbol": payload.symbol,
            "timeframe": payload.timeframe,
            "from_date": payload.from_date,
            "to_date": payload.to_date,
            "commission_pct": payload.commission_pct,
            "slippage_pct": payload.slippage_pct,
            "stop_loss_pct": payload.stop_loss_pct,
            "take_profit_pct": payload.take_profit_pct,
            "position_sizing_mode": payload.position_sizing_mode,
            "fixed_quantity": payload.fixed_quantity,
            "capital_per_trade": payload.capital_per_trade,
            "equity_pct_per_trade": payload.equity_pct_per_trade,
            "metrics": metrics,
            "trades": raw["trades"],
            "equity_curve": raw["equity_curve"],
            "market_data": market_data,
            "chart_html": chart_html,
            "drawdown_chart_html": drawdown_chart_html,
        }
