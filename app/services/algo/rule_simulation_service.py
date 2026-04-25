from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.schemas.algo_schema import AlgoRuleCondition, AlgoSimulationRequest, AlgoStrategyLeg
from app.services.analytics.metrics_service import MetricsService
from app.services.data.data_loader_service import DataLoaderService
from app.services.data.date_range_filter_service import DateRangeFilterService
from app.services.indicators.atr_service import ATRService
from app.services.indicators.ema_service import EMAService
from app.services.indicators.macd_service import MACDService
from app.services.indicators.rsi_service import RSIService
from app.services.indicators.sma_service import SMAService


@dataclass
class OpenAlgoPosition:
    direction: int
    entry_price: float
    entry_time: str
    quantity: int
    capital_used: float
    entry_reason: str
    entry_index: int
    stop_price: float | None = None
    target_prices: list[tuple[float, float]] | None = None
    remaining_quantity: int = 0
    realized_pnl: float = 0.0
    target_hit: bool = False
    stop_loss_hit: bool = False
    highest_price: float = 0.0
    lowest_price: float = 0.0


class AlgoRuleSimulationService:
    def __init__(self) -> None:
        self.loader = DataLoaderService()
        self.date_filter = DateRangeFilterService()
        self.metrics = MetricsService()

    def simulate(self, payload: AlgoSimulationRequest) -> dict[str, Any]:
        warnings = self.validate_payload(payload)
        frame = self.loader.load(payload.source, payload.file_name)
        frame = self.date_filter.filter(frame, payload.from_date, payload.to_date).reset_index(drop=True)
        prepared = self._prepare_indicators(frame, self._all_conditions(payload))
        entry_signal, entry_reasons = self._entry_signal(prepared, payload)
        exit_signal, exit_reasons = self._exit_signal(prepared, payload)
        entry_signal = self._limit_trades_per_day(prepared, entry_signal, payload.max_trades_per_day)
        raw = self._simulate_trades(prepared, entry_signal, entry_reasons, exit_signal, exit_reasons, payload)
        metrics = self.metrics.calculate(payload.initial_capital, raw["ending_equity"], raw["trades"], raw["equity_curve"])
        pnls = [float(trade.get("pnl", 0)) for trade in raw["trades"]]
        wins = sum(1 for value in pnls if value > 0)
        losses = sum(1 for value in pnls if value <= 0)
        gross_profit = round(sum(value for value in pnls if value > 0), 2)
        gross_loss = round(abs(sum(value for value in pnls if value < 0)), 2)
        expectancy = round(sum(pnls) / len(pnls), 2) if pnls else 0.0
        return {
            "symbol": payload.symbol,
            "exchange": payload.exchange,
            "timeframe": payload.timeframe,
            "signal_count": int(entry_signal.sum() + exit_signal.sum()),
            "buy_signal_count": int(entry_signal.sum()),
            "sell_signal_count": int(exit_signal.sum()),
            "exit_signal_count": int(exit_signal.sum()),
            "estimated_net_profit": metrics["net_profit"],
            "estimated_loss": gross_loss,
            "win_rate": metrics["win_rate_pct"],
            "max_drawdown": metrics["max_drawdown_pct"],
            "wins": wins,
            "losses": losses,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "expectancy": expectancy,
            "validation_warnings": warnings,
            "metrics": metrics,
            "trades": raw["trades"],
            "equity_curve": raw["equity_curve"],
        }

    def validate_payload(self, payload: AlgoSimulationRequest) -> list[str]:
        warnings: list[str] = []
        legs = self._legs(payload)
        if not legs:
            warnings.append("No entry legs were defined.")
        for leg in legs:
            if not leg.conditions:
                warnings.append(f"{leg.name} has no conditions.")
            sources = {condition.source for condition in leg.conditions}
            for source in sources:
                gt = [c.value for c in leg.conditions if c.source == source and c.operator in {">", ">="}]
                lt = [c.value for c in leg.conditions if c.source == source and c.operator in {"<", "<="}]
                if gt and lt and max(gt) >= min(lt) and payload.require_all_conditions:
                    warnings.append(f"{leg.name} may contain conflicting {source} thresholds.")
        if payload.exits.stop_type == "none" and payload.exits.target_type == "none" and not payload.exits.exit_conditions:
            warnings.append("No stop, target, or exit condition is configured.")
        if payload.position.action in {"Sell", "Short"}:
            warnings.append("Short-side simulation is supported, but live broker execution is disabled.")
        return warnings

    def _legs(self, payload: AlgoSimulationRequest) -> list[AlgoStrategyLeg]:
        if payload.legs:
            return payload.legs
        return [AlgoStrategyLeg(name="Entry", conditions=[c for c in payload.conditions if c.signal_type == "buy"] or payload.conditions)]

    def _all_conditions(self, payload: AlgoSimulationRequest) -> list[AlgoRuleCondition]:
        conditions = list(payload.conditions)
        for leg in payload.legs:
            conditions.extend(leg.conditions)
        conditions.extend(payload.exits.exit_conditions)
        return conditions

    def _prepare_indicators(self, frame: pd.DataFrame, conditions: list[AlgoRuleCondition]) -> pd.DataFrame:
        prepared = frame.copy()
        close = prepared["Close"].astype(float)
        prepared["algo_price"] = close
        prepared["algo_open"] = prepared["Open"].astype(float)
        prepared["algo_high"] = prepared["High"].astype(float)
        prepared["algo_low"] = prepared["Low"].astype(float)
        prepared["algo_volume"] = prepared["Volume"].astype(float)
        prepared["algo_vwap"] = self._vwap(prepared)
        prepared["algo_atr_14"] = ATRService().calculate(prepared["High"], prepared["Low"], prepared["Close"], 14).fillna(0)
        prepared["algo_rsi_14"] = RSIService().calculate(close, 14).fillna(50)
        macd = MACDService().calculate(close)
        prepared["algo_macd"] = macd["macd"].fillna(0)
        for condition in conditions:
            period = condition.period or self._default_period(condition.source)
            self._ensure_timeframe_source(prepared, condition.source, period, condition.timeframe)
            if condition.source == "EMA":
                prepared[f"algo_ema_{period}"] = EMAService().calculate(close, period).fillna(close)
            if condition.source == "SMA":
                prepared[f"algo_sma_{period}"] = SMAService().calculate(close, period).fillna(close)
            if condition.source == "RSI":
                prepared[f"algo_rsi_{period}"] = RSIService().calculate(close, period).fillna(50)
            if condition.source == "ATR":
                prepared[f"algo_atr_{period}"] = ATRService().calculate(prepared["High"], prepared["Low"], prepared["Close"], period).fillna(0)
            if condition.compare_source:
                compare_period = condition.compare_period or self._default_period(condition.compare_source)
                self._ensure_timeframe_source(prepared, condition.compare_source, compare_period, condition.timeframe)
                if condition.compare_source == "EMA":
                    prepared[f"algo_ema_{compare_period}"] = EMAService().calculate(close, compare_period).fillna(close)
                if condition.compare_source == "SMA":
                    prepared[f"algo_sma_{compare_period}"] = SMAService().calculate(close, compare_period).fillna(close)
        return prepared

    def _entry_signal(self, frame: pd.DataFrame, payload: AlgoSimulationRequest) -> tuple[pd.Series, list[str]]:
        legs = self._legs(payload)
        leg_signals = []
        reasons = []
        for leg in legs:
            signal = self._signal_for_conditions(frame, leg.conditions, payload.require_all_conditions)
            leg_signals.append(signal)
            reasons.append(leg.name)
        if not leg_signals:
            return pd.Series(False, index=frame.index), []
        combined = leg_signals[0]
        for leg, signal in zip(legs[1:], leg_signals[1:]):
            combined = combined | signal if leg.connector == "OR" else combined & signal
        return combined.fillna(False), reasons

    def _exit_signal(self, frame: pd.DataFrame, payload: AlgoSimulationRequest) -> tuple[pd.Series, list[str]]:
        legacy = [c for c in payload.conditions if c.signal_type in {"sell", "exit"}]
        conditions = [*legacy, *payload.exits.exit_conditions]
        signal = self._signal_for_conditions(frame, conditions, False) if conditions else pd.Series(False, index=frame.index)
        return signal.fillna(False), ["Exit rule"] if conditions else []

    def _signal_for_conditions(self, frame: pd.DataFrame, conditions: list[AlgoRuleCondition], require_all: bool) -> pd.Series:
        if not conditions:
            return pd.Series(False, index=frame.index)
        signals = [self._condition_signal(frame, condition) for condition in conditions]
        combined = signals[0]
        if require_all:
            for signal in signals[1:]:
                combined = combined & signal
        else:
            for condition, signal in zip(conditions[1:], signals[1:]):
                combined = combined | signal if condition.connector == "OR" else combined & signal
        return combined.fillna(False)

    def _condition_signal(self, frame: pd.DataFrame, condition: AlgoRuleCondition) -> pd.Series:
        left = self._source_series(frame, condition.source, condition.period, condition.timeframe)
        right = (
            self._source_series(frame, condition.compare_source, condition.compare_period, condition.timeframe)
            if condition.compare_source
            else float(condition.value)
        )
        if condition.operator == ">":
            return left > right
        if condition.operator == "<":
            return left < right
        if condition.operator == ">=":
            return left >= right
        if condition.operator == "<=":
            return left <= right
        if condition.operator == "crosses above":
            return (left.shift(1) <= (right.shift(1) if hasattr(right, "shift") else right)) & (left > right)
        if condition.operator == "crosses below":
            return (left.shift(1) >= (right.shift(1) if hasattr(right, "shift") else right)) & (left < right)
        return pd.Series(False, index=frame.index)

    def _source_series(self, frame: pd.DataFrame, source: str | None, period: int | None, timeframe: str = "Daily") -> pd.Series:
        source = source or "Price"
        period = period or self._default_period(source)
        key = self._timeframe_key(source, period, timeframe)
        if key in frame:
            return frame[key]
        mapping = {
            "Price": "algo_price",
            "Open": "algo_open",
            "High": "algo_high",
            "Low": "algo_low",
            "Volume": "algo_volume",
            "VWAP": "algo_vwap",
            "MACD": "algo_macd",
        }
        if source in mapping:
            return frame[mapping[source]]
        if source == "EMA":
            return frame[f"algo_ema_{period}"]
        if source == "SMA":
            return frame[f"algo_sma_{period}"]
        if source == "RSI":
            return frame[f"algo_rsi_{period}"]
        if source == "ATR":
            return frame[f"algo_atr_{period}"]
        return frame["algo_price"]

    def _ensure_timeframe_source(self, frame: pd.DataFrame, source: str, period: int, timeframe: str) -> None:
        key = self._timeframe_key(source, period, timeframe)
        if key in frame or timeframe in {"Intraday", "Daily"}:
            return
        resampled = self._resampled_frame(frame, timeframe)
        if resampled.empty:
            frame[key] = self._source_series(frame, source, period, "Daily")
            return
        close = resampled["Close"].astype(float)
        if source == "Price":
            series = close
        elif source == "Open":
            series = resampled["Open"].astype(float)
        elif source == "High":
            series = resampled["High"].astype(float)
        elif source == "Low":
            series = resampled["Low"].astype(float)
        elif source == "Volume":
            series = resampled["Volume"].astype(float)
        elif source == "VWAP":
            series = self._vwap(resampled.reset_index().rename(columns={"index": "Date"}))
        elif source == "EMA":
            series = EMAService().calculate(close, period).fillna(close)
        elif source == "SMA":
            series = SMAService().calculate(close, period).fillna(close)
        elif source == "RSI":
            series = RSIService().calculate(close, period).fillna(50)
        elif source == "ATR":
            series = ATRService().calculate(resampled["High"], resampled["Low"], resampled["Close"], period).fillna(0)
        elif source == "MACD":
            series = MACDService().calculate(close)["macd"].fillna(0)
        else:
            series = close
        frame_dates = pd.to_datetime(frame["Date"], errors="coerce")
        frame[key] = series.reindex(frame_dates, method="ffill").bfill().to_numpy()

    def _resampled_frame(self, frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        rule = {"Weekly": "W-FRI", "Monthly": "ME"}.get(timeframe)
        if not rule:
            return pd.DataFrame()
        prepared = frame.copy()
        prepared["_algo_date"] = pd.to_datetime(prepared["Date"], errors="coerce")
        prepared = prepared.dropna(subset=["_algo_date"]).set_index("_algo_date").sort_index()
        return (
            prepared.resample(rule)
            .agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
            .dropna()
        )

    def _timeframe_key(self, source: str, period: int, timeframe: str) -> str:
        suffix = timeframe.lower()
        if timeframe in {"Intraday", "Daily"}:
            suffix = "base"
        return f"algo_{source.lower()}_{period}_{suffix}"

    def _simulate_trades(
        self,
        frame: pd.DataFrame,
        entry_signal: pd.Series,
        entry_reasons: list[str],
        exit_signal: pd.Series,
        exit_reasons: list[str],
        payload: AlgoSimulationRequest,
    ) -> dict[str, Any]:
        cash = float(payload.initial_capital)
        position: OpenAlgoPosition | None = None
        trades: list[dict[str, Any]] = []
        equity_curve: list[dict[str, Any]] = []
        direction = -1 if payload.position.action in {"Sell", "Short"} else 1
        for index, row in frame.iterrows():
            close = float(row["Close"])
            high = float(row["High"])
            low = float(row["Low"])
            timestamp = str(row["Date"])
            if position:
                position.highest_price = max(position.highest_price, high)
                position.lowest_price = min(position.lowest_price, low)
                cash, target_exit = self._apply_partial_targets(cash, position, high, low, timestamp, payload)
                if target_exit:
                    trade = self._close_position(cash, position, target_exit[0], timestamp, target_exit[1], payload)[1]
                    trades.append(trade)
                    position = None
                    equity_curve.append({"timestamp": timestamp, "equity": round(cash, 2)})
                    continue
                exit_reason = self._exit_reason(position, row, index, bool(exit_signal.iloc[index]), payload)
                if exit_reason:
                    cash, trade = self._close_position(cash, position, close, timestamp, exit_reason, payload)
                    trades.append(trade)
                    position = None
            if position is None and bool(entry_signal.iloc[index]):
                quantity, capital_used = self._position_size(cash, close, payload)
                if quantity > 0:
                    cash -= capital_used
                    stop_price = self._initial_stop(close, float(row.get("algo_atr_14", 0)), direction, payload)
                    position = OpenAlgoPosition(
                        direction=direction,
                        entry_price=close,
                        entry_time=timestamp,
                        quantity=quantity,
                        remaining_quantity=quantity,
                        capital_used=capital_used,
                        entry_reason=", ".join(entry_reasons) or "Entry rules",
                        entry_index=index,
                        stop_price=stop_price,
                        target_prices=self._target_prices(close, direction, payload),
                        highest_price=high,
                        lowest_price=low,
                    )
            open_value = position.remaining_quantity * close if position else 0.0
            if position and position.direction < 0:
                remaining_capital = position.capital_used * (position.remaining_quantity / position.quantity)
                open_value = remaining_capital + (position.entry_price - close) * position.remaining_quantity
            equity_curve.append({"timestamp": timestamp, "equity": round(cash + open_value, 2)})
        if position:
            cash, trade = self._close_position(
                cash,
                position,
                float(frame.iloc[-1]["Close"]),
                str(frame.iloc[-1]["Date"]),
                "end_of_data",
                payload,
            )
            trades.append(trade)
            equity_curve[-1]["equity"] = round(cash, 2)
        return {"trades": trades, "equity_curve": equity_curve, "ending_equity": round(cash, 2)}

    def _position_size(self, cash: float, price: float, payload: AlgoSimulationRequest) -> tuple[int, float]:
        mode = payload.position.sizing_mode
        if mode in {"quantity", "fixed_quantity"}:
            quantity = payload.position.quantity or payload.position.fixed_quantity or 1
        else:
            capital = cash * (payload.position.capital_allocation_pct / 100)
            if mode == "risk_pct" and payload.position.risk_per_trade_pct and payload.exits.stop_loss_pct:
                risk_amount = cash * (payload.position.risk_per_trade_pct / 100)
                per_share_risk = price * (payload.exits.stop_loss_pct / 100)
                quantity = int(risk_amount // per_share_risk) if per_share_risk > 0 else 0
            else:
                quantity = int(capital // price)
        capital_used = quantity * price
        if capital_used > cash:
            quantity = int(cash // price)
            capital_used = quantity * price
        return quantity, capital_used

    def _initial_stop(self, price: float, atr: float, direction: int, payload: AlgoSimulationRequest) -> float | None:
        exits = payload.exits
        if exits.stop_type == "fixed_pct" and exits.stop_loss_pct:
            return price * (1 - direction * exits.stop_loss_pct / 100)
        if exits.stop_type == "atr" and exits.atr_multiplier:
            return price - direction * atr * exits.atr_multiplier
        if exits.stop_type == "trailing_pct" and exits.trailing_stop_pct:
            return price * (1 - direction * exits.trailing_stop_pct / 100)
        if payload.stop_loss_pct:
            return price * (1 - direction * payload.stop_loss_pct / 100)
        return None

    def _target_prices(self, price: float, direction: int, payload: AlgoSimulationRequest) -> list[tuple[float, float]]:
        exits = payload.exits
        if exits.target_type == "multi_target" and exits.targets:
            return [(price * (1 + direction * target.target_pct / 100), target.exit_pct) for target in exits.targets]
        target_pct = exits.target_pct or payload.target_pct
        return [(price * (1 + direction * target_pct / 100), 100.0)] if target_pct else []

    def _exit_reason(self, position: OpenAlgoPosition, row: pd.Series, index: int, exit_rule: bool, payload: AlgoSimulationRequest) -> str | None:
        high = float(row["High"])
        low = float(row["Low"])
        if payload.exits.stop_type == "trailing_pct" and payload.exits.trailing_stop_pct:
            if position.direction > 0:
                position.stop_price = max(position.stop_price or 0, position.highest_price * (1 - payload.exits.trailing_stop_pct / 100))
            else:
                position.stop_price = min(position.stop_price or float("inf"), position.lowest_price * (1 + payload.exits.trailing_stop_pct / 100))
        if position.stop_price is not None:
            if (position.direction > 0 and low <= position.stop_price) or (position.direction < 0 and high >= position.stop_price):
                position.stop_loss_hit = True
                return "stop_loss"
        if payload.exits.max_bars_in_trade and index - position.entry_index >= payload.exits.max_bars_in_trade:
            return "time_exit"
        if exit_rule:
            return "exit_rule"
        return None

    def _apply_partial_targets(
        self,
        cash: float,
        position: OpenAlgoPosition,
        high: float,
        low: float,
        exit_time: str,
        payload: AlgoSimulationRequest,
    ) -> tuple[float, tuple[float, str] | None]:
        remaining_targets: list[tuple[float, float]] = []
        close_signal: tuple[float, str] | None = None
        for target_price, exit_pct in position.target_prices or []:
            hit = (position.direction > 0 and high >= target_price) or (position.direction < 0 and low <= target_price)
            if not hit or position.remaining_quantity <= 0:
                remaining_targets.append((target_price, exit_pct))
                continue
            position.target_hit = True
            exit_quantity = min(position.remaining_quantity, max(1, int(position.quantity * (exit_pct / 100))))
            gross_pnl = (target_price - position.entry_price) * exit_quantity * position.direction
            turnover = (position.entry_price + target_price) * exit_quantity
            costs = turnover * ((payload.commission_pct + payload.slippage_pct) / 100)
            pnl = gross_pnl - costs
            released_capital = position.capital_used * (exit_quantity / position.quantity)
            position.realized_pnl += pnl
            position.remaining_quantity -= exit_quantity
            cash += released_capital + pnl
            if position.remaining_quantity <= 0:
                close_signal = (target_price, f"target_{exit_pct:g}_pct_exit")
                break
        position.target_prices = remaining_targets
        return cash, close_signal

    def _close_position(
        self,
        cash: float,
        position: OpenAlgoPosition,
        exit_price: float,
        exit_time: str,
        exit_reason: str,
        payload: AlgoSimulationRequest,
    ) -> tuple[float, dict[str, Any]]:
        close_quantity = position.remaining_quantity
        gross_pnl = (exit_price - position.entry_price) * close_quantity * position.direction
        turnover = (position.entry_price + exit_price) * close_quantity
        brokerage_cost = turnover * (payload.commission_pct / 100)
        slippage_cost = turnover * (payload.slippage_pct / 100)
        closing_pnl = gross_pnl - brokerage_cost - slippage_cost
        pnl = position.realized_pnl + closing_pnl
        remaining_capital = position.capital_used * (close_quantity / position.quantity) if position.quantity else 0.0
        proceeds = remaining_capital + closing_pnl
        trade = {
            "entry_time": position.entry_time,
            "exit_time": exit_time,
            "entry_price": round(position.entry_price, 2),
            "exit_price": round(exit_price, 2),
            "exit_reason": exit_reason,
            "entry_reason": position.entry_reason,
            "position_sizing_mode": "algo_custom",
            "quantity": position.quantity,
            "capital_used": round(position.capital_used, 2),
            "gross_pnl": round(gross_pnl, 2),
            "brokerage_cost": round(brokerage_cost, 2),
            "slippage_cost": round(slippage_cost, 2),
            "pnl": round(pnl, 2),
            "return_pct": round((pnl / position.capital_used) * 100, 2) if position.capital_used else 0.0,
            "stop_loss_hit": position.stop_loss_hit,
            "target_hit": position.target_hit,
        }
        return cash + proceeds, trade

    def _limit_trades_per_day(self, frame: pd.DataFrame, signal: pd.Series, max_trades_per_day: int) -> pd.Series:
        dates = pd.to_datetime(frame["Date"], errors="coerce").dt.date
        counts: dict[Any, int] = defaultdict(int)
        limited = []
        for date_value, is_signal in zip(dates, signal):
            if is_signal and counts[date_value] < max_trades_per_day:
                counts[date_value] += 1
                limited.append(True)
            else:
                limited.append(False)
        return pd.Series(limited, index=frame.index)

    def _vwap(self, frame: pd.DataFrame) -> pd.Series:
        typical = (frame["High"].astype(float) + frame["Low"].astype(float) + frame["Close"].astype(float)) / 3
        volume = frame["Volume"].astype(float)
        return (typical * volume).cumsum() / volume.replace(0, pd.NA).cumsum()

    def _default_period(self, source: str | None) -> int:
        return {"EMA": 20, "SMA": 20, "RSI": 14, "ATR": 14}.get(source or "", 14)
