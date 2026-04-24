from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from app.schemas.algo_schema import AlgoRuleCondition, AlgoSimulationRequest
from app.services.analytics.metrics_service import MetricsService
from app.services.backtesting.engine import BacktestEngine
from app.services.data.data_loader_service import DataLoaderService
from app.services.data.date_range_filter_service import DateRangeFilterService
from app.services.indicators.ema_service import EMAService
from app.services.indicators.macd_service import MACDService
from app.services.indicators.rsi_service import RSIService


class AlgoRuleSimulationService:
    def __init__(self) -> None:
        self.loader = DataLoaderService()
        self.date_filter = DateRangeFilterService()
        self.engine = BacktestEngine()
        self.metrics = MetricsService()

    def simulate(self, payload: AlgoSimulationRequest) -> dict[str, Any]:
        frame = self.loader.load(payload.source, payload.file_name)
        frame = self.date_filter.filter(frame, payload.from_date, payload.to_date)
        signal_frame = self._apply_rules(frame, payload)
        raw = self.engine.run(
            signal_frame,
            payload.initial_capital,
            payload.commission_pct,
            payload.slippage_pct,
            payload.position_sizing_mode,
            fixed_quantity=None,
            capital_per_trade=payload.position_size,
            equity_pct_per_trade=None,
            stop_loss_pct=payload.stop_loss_pct,
            take_profit_pct=payload.target_pct,
        )
        metrics = self.metrics.calculate(
            payload.initial_capital,
            raw["ending_equity"],
            raw["trades"],
            raw["equity_curve"],
        )
        estimated_loss = abs(sum(float(trade.get("pnl", 0)) for trade in raw["trades"] if float(trade.get("pnl", 0)) < 0))
        return {
            "symbol": payload.symbol,
            "exchange": payload.exchange,
            "timeframe": payload.timeframe,
            "signal_count": int(signal_frame["buy_signal"].sum() + signal_frame["sell_signal"].sum() + signal_frame["algo_exit_signal"].sum()),
            "buy_signal_count": int(signal_frame["buy_signal"].sum()),
            "sell_signal_count": int(signal_frame["sell_signal"].sum()),
            "exit_signal_count": int(signal_frame["algo_exit_signal"].sum()),
            "estimated_net_profit": metrics["net_profit"],
            "estimated_loss": round(estimated_loss, 2),
            "win_rate": metrics["win_rate_pct"],
            "max_drawdown": metrics["max_drawdown_pct"],
            "metrics": metrics,
            "trades": raw["trades"],
            "equity_curve": raw["equity_curve"],
        }

    def _apply_rules(self, frame: pd.DataFrame, payload: AlgoSimulationRequest) -> pd.DataFrame:
        prepared = self._prepare_indicators(frame, payload.conditions)
        grouped = self._group_conditions(payload.conditions)
        prepared["buy_signal"] = self._signal_for_group(prepared, grouped["buy"], payload.require_all_conditions)
        sell_signal = self._signal_for_group(prepared, grouped["sell"], payload.require_all_conditions)
        exit_signal = self._signal_for_group(prepared, grouped["exit"], payload.require_all_conditions)
        prepared["algo_exit_signal"] = exit_signal
        prepared["sell_signal"] = sell_signal | exit_signal
        prepared["buy_signal"] = self._limit_trades_per_day(prepared, prepared["buy_signal"], payload.max_trades_per_day)
        return prepared

    def _prepare_indicators(self, frame: pd.DataFrame, conditions: list[AlgoRuleCondition]) -> pd.DataFrame:
        prepared = frame.copy()
        close = prepared["Close"].astype(float)
        prepared["algo_price"] = close
        prepared["algo_volume"] = prepared["Volume"].astype(float)
        prepared["algo_rsi"] = RSIService().calculate(close, 14).fillna(50)
        macd = MACDService().calculate(close)
        prepared["algo_macd"] = macd["macd"].fillna(0)
        for condition in conditions:
            if condition.source == "EMA":
                period = condition.period or (int(condition.value) if condition.value > 1 else 20)
                key = f"algo_ema_{period}"
                if key not in prepared:
                    prepared[key] = EMAService().calculate(close, period).fillna(close)
        return prepared

    def _group_conditions(self, conditions: list[AlgoRuleCondition]) -> dict[str, list[AlgoRuleCondition]]:
        grouped: dict[str, list[AlgoRuleCondition]] = defaultdict(list)
        for condition in conditions:
            grouped[condition.signal_type].append(condition)
        return grouped

    def _signal_for_group(
        self,
        frame: pd.DataFrame,
        conditions: list[AlgoRuleCondition],
        require_all_conditions: bool,
    ) -> pd.Series:
        if not conditions:
            return pd.Series(False, index=frame.index)

        signals = [self._condition_signal(frame, condition) for condition in conditions]
        if require_all_conditions:
            combined = signals[0]
            for signal in signals[1:]:
                combined = combined & signal
            return combined.fillna(False)

        combined = signals[0]
        for condition, signal in zip(conditions[1:], signals[1:]):
            combined = combined | signal if condition.connector == "OR" else combined & signal
        return combined.fillna(False)

    def _condition_signal(self, frame: pd.DataFrame, condition: AlgoRuleCondition) -> pd.Series:
        series = self._source_series(frame, condition)
        value = float(condition.value)
        if condition.operator == ">":
            return series > value
        if condition.operator == "<":
            return series < value
        if condition.operator == ">=":
            return series >= value
        if condition.operator == "<=":
            return series <= value
        if condition.operator == "crosses above":
            return (series.shift(1) <= value) & (series > value)
        if condition.operator == "crosses below":
            return (series.shift(1) >= value) & (series < value)
        return pd.Series(False, index=frame.index)

    def _source_series(self, frame: pd.DataFrame, condition: AlgoRuleCondition) -> pd.Series:
        if condition.source == "Price":
            return frame["algo_price"]
        if condition.source == "Volume":
            return frame["algo_volume"]
        if condition.source == "RSI":
            return frame["algo_rsi"]
        if condition.source == "MACD":
            return frame["algo_macd"]
        if condition.source == "EMA":
            period = condition.period or (int(condition.value) if condition.value > 1 else 20)
            return frame[f"algo_ema_{period}"]
        return pd.Series(0, index=frame.index)

    def _limit_trades_per_day(self, frame: pd.DataFrame, signal: pd.Series, max_trades_per_day: int) -> pd.Series:
        dates = pd.to_datetime(frame["Date"], errors="coerce").dt.date
        counts: dict[Any, int] = defaultdict(int)
        limited = []
        for date_value, is_signal in zip(dates, signal):
            if not is_signal:
                limited.append(False)
                continue
            if counts[date_value] >= max_trades_per_day:
                limited.append(False)
                continue
            counts[date_value] += 1
            limited.append(True)
        return pd.Series(limited, index=frame.index)
