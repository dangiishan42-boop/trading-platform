import pandas as pd

from app.schemas.backtest_schema import BacktestRunRequest
from app.schemas.portfolio_backtest_schema import PortfolioBacktestRequest, RebalancingMode
from app.services.analytics.metrics_service import MetricsService
from app.services.backtesting.runner import BacktestRunner


class PortfolioBacktestService:
    def __init__(
        self,
        runner: BacktestRunner | None = None,
        metrics_service: MetricsService | None = None,
    ) -> None:
        self.runner = runner or BacktestRunner()
        self.metrics_service = metrics_service or MetricsService()

    def run(self, payload: PortfolioBacktestRequest) -> dict:
        symbol_results: list[dict] = []
        portfolio_trades: list[dict] = []

        for dataset in payload.datasets:
            allocated_capital = payload.initial_capital * (dataset.allocation_pct / 100)
            symbol_payload = BacktestRunRequest(
                source=dataset.source,
                file_name=dataset.file_name,
                symbol=dataset.symbol,
                timeframe=dataset.timeframe,
                strategy_name=payload.strategy_name,
                initial_capital=allocated_capital,
                commission_pct=payload.commission_pct,
                slippage_pct=payload.slippage_pct,
                stop_loss_pct=payload.stop_loss_pct,
                take_profit_pct=payload.take_profit_pct,
                position_sizing_mode=payload.position_sizing_mode,
                fixed_quantity=payload.fixed_quantity,
                capital_per_trade=payload.capital_per_trade,
                equity_pct_per_trade=payload.equity_pct_per_trade,
                parameters=payload.parameters,
            )
            result = self.runner.run(symbol_payload)
            symbol_results.append(
                {
                    "symbol": dataset.symbol,
                    "source": dataset.source,
                    "file_name": dataset.file_name,
                    "timeframe": dataset.timeframe,
                    "allocation_pct": dataset.allocation_pct,
                    "allocated_capital": round(allocated_capital, 2),
                    "metrics": result["metrics"],
                    "trades": result["trades"],
                    "equity_curve": result["equity_curve"],
                }
            )
            portfolio_trades.extend(result["trades"])

        portfolio_equity_curve = self._combine_equity_curves(
            symbol_results,
            payload.rebalancing_mode,
        )
        ending_equity = portfolio_equity_curve[-1]["equity"] if portfolio_equity_curve else payload.initial_capital
        metrics = self.metrics_service.calculate(
            payload.initial_capital,
            ending_equity,
            portfolio_trades,
            portfolio_equity_curve,
        )

        return {
            "strategy_name": payload.strategy_name,
            "rebalancing_mode": payload.rebalancing_mode,
            "initial_capital": payload.initial_capital,
            "metrics": metrics,
            "equity_curve": portfolio_equity_curve,
            "symbol_results": symbol_results,
        }

    def _combine_equity_curves(
        self,
        symbol_results: list[dict],
        rebalancing_mode: RebalancingMode = "none",
    ) -> list[dict]:
        combined = self._build_symbol_equity_frame(symbol_results)
        if combined.empty:
            return []

        if rebalancing_mode == "none":
            return self._sum_symbol_equity_frame(combined)

        return self._combine_with_rebalancing(
            combined,
            symbol_results,
            rebalancing_mode,
        )

    def _build_symbol_equity_frame(self, symbol_results: list[dict]) -> pd.DataFrame:
        timestamps = sorted(
            {
                point["timestamp"]
                for result in symbol_results
                for point in result["equity_curve"]
            },
            key=self._timestamp_sort_key,
        )
        if not timestamps:
            return pd.DataFrame()

        combined = pd.DataFrame({"timestamp": timestamps})
        for index, result in enumerate(symbol_results):
            equity_by_timestamp = {
                point["timestamp"]: float(point["equity"])
                for point in result["equity_curve"]
            }
            column_name = f"symbol_{index}"
            combined[column_name] = combined["timestamp"].map(equity_by_timestamp)
            combined[column_name] = combined[column_name].ffill().fillna(result["allocated_capital"])
        return combined

    def _sum_symbol_equity_frame(self, combined: pd.DataFrame) -> list[dict]:
        equity_columns = [column for column in combined.columns if column != "timestamp"]
        combined["equity"] = combined[equity_columns].sum(axis=1).round(2)
        return combined[["timestamp", "equity"]].to_dict(orient="records")

    def _combine_with_rebalancing(
        self,
        combined: pd.DataFrame,
        symbol_results: list[dict],
        rebalancing_mode: RebalancingMode,
    ) -> list[dict]:
        equity_columns = [column for column in combined.columns if column != "timestamp"]
        target_weights = [
            float(result["allocation_pct"]) / 100
            for result in symbol_results
        ]
        values: list[float] | None = None
        previous_underlying: list[float] | None = None
        previous_period_key: tuple[int, int] | None = None
        rows: list[dict] = []

        for _, row in combined.iterrows():
            timestamp = row["timestamp"]
            underlying = [float(row[column]) for column in equity_columns]
            current_period_key = self._rebalance_period_key(timestamp, rebalancing_mode)

            if values is None:
                values = underlying.copy()
            elif previous_underlying is not None:
                # First-version rebalance model: keep each sleeve invested between
                # rebalance dates, then reset sleeves to target weights on boundaries.
                values = [
                    value * self._safe_return_ratio(current, previous)
                    for value, current, previous in zip(values, underlying, previous_underlying)
                ]
                if self._is_rebalance_boundary(previous_period_key, current_period_key):
                    total_value = sum(values)
                    values = [total_value * weight for weight in target_weights]

            rows.append({"timestamp": timestamp, "equity": round(sum(values), 2)})
            previous_underlying = underlying
            previous_period_key = current_period_key

        return rows

    def _safe_return_ratio(self, current: float, previous: float) -> float:
        if previous == 0:
            return 1.0
        return current / previous

    def _is_rebalance_boundary(
        self,
        previous_period_key: tuple[int, int] | None,
        current_period_key: tuple[int, int] | None,
    ) -> bool:
        if previous_period_key is None or current_period_key is None:
            return False
        return previous_period_key != current_period_key

    def _rebalance_period_key(
        self,
        timestamp: str,
        rebalancing_mode: RebalancingMode,
    ) -> tuple[int, int] | None:
        parsed = pd.to_datetime(timestamp, errors="coerce")
        if pd.isna(parsed):
            return None
        if rebalancing_mode == "quarterly":
            return (parsed.year, ((parsed.month - 1) // 3) + 1)
        return (parsed.year, parsed.month)

    def _timestamp_sort_key(self, value: str) -> tuple[int, object]:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return (1, value)
        return (0, parsed.to_pydatetime())
