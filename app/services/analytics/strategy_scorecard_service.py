from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any

import pandas as pd

from app.core.exceptions import InvalidRequestError


class StrategyScorecardService:
    TRADING_DAYS_PER_YEAR = 252

    def calculate(
        self,
        *,
        initial_capital: float,
        equity_curve: list[dict[str, Any]],
        trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if initial_capital <= 0:
            raise InvalidRequestError("initial_capital must be greater than zero")
        if len(equity_curve) < 2:
            raise InvalidRequestError("Scorecard requires at least two equity curve points")

        equity_frame = self._equity_frame(equity_curve)
        if len(equity_frame) < 2:
            raise InvalidRequestError("Scorecard requires valid equity timestamps and values")

        returns = equity_frame["equity"].pct_change().dropna().tolist()
        ending_equity = float(equity_frame.iloc[-1]["equity"])
        net_profit = ending_equity - initial_capital
        max_drawdown_pct, max_drawdown_amount = self._max_drawdown(equity_frame["equity"].tolist())
        cagr = self._cagr(initial_capital, ending_equity, equity_frame)
        sharpe = self._sharpe_ratio(returns)
        sortino = self._sortino_ratio(returns)
        calmar = round(cagr / max_drawdown_pct, 4) if max_drawdown_pct > 0 else 0.0
        profit_factor = self._profit_factor(trades)
        expectancy = self._expectancy(trades)
        avg_win = self._average_pnl(trades, wins=True)
        avg_loss = self._average_pnl(trades, wins=False)
        exposure_pct = self._exposure_pct(trades, equity_frame)
        recovery_factor = round(net_profit / max_drawdown_amount, 4) if max_drawdown_amount > 0 else 0.0

        metrics = {
            "cagr": round(cagr, 2),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "exposure_pct": exposure_pct,
            "recovery_factor": recovery_factor,
        }
        return {
            "metrics": metrics,
            "highlights": self._highlights(metrics),
            "warnings": self._warnings(metrics, max_drawdown_pct),
            "method": (
                "V1 scorecard uses equity-curve percentage changes with 252-period annualization. "
                "CAGR is based on first and last equity timestamps; trade metrics use completed trade PnL."
            ),
        }

    def _equity_frame(self, equity_curve: list[dict[str, Any]]) -> pd.DataFrame:
        frame = pd.DataFrame(equity_curve)
        if "timestamp" not in frame.columns or "equity" not in frame.columns:
            raise InvalidRequestError("equity_curve must include timestamp and equity values")
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame["equity"] = pd.to_numeric(frame["equity"], errors="coerce")
        return frame.dropna(subset=["timestamp", "equity"]).sort_values("timestamp").reset_index(drop=True)

    def _cagr(self, initial_capital: float, ending_equity: float, equity_frame: pd.DataFrame) -> float:
        first = equity_frame.iloc[0]["timestamp"]
        last = equity_frame.iloc[-1]["timestamp"]
        days = max((last - first).total_seconds() / 86400, 1)
        years = days / 365.25
        if ending_equity <= 0:
            return -100.0
        return ((ending_equity / initial_capital) ** (1 / years) - 1) * 100

    def _sharpe_ratio(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        volatility = pstdev(returns)
        if volatility == 0:
            return 0.0
        return round((mean(returns) / volatility) * math.sqrt(self.TRADING_DAYS_PER_YEAR), 4)

    def _sortino_ratio(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        downside = [value for value in returns if value < 0]
        downside_deviation = pstdev(downside) if len(downside) > 1 else 0.0
        if downside_deviation == 0:
            return 0.0
        return round((mean(returns) / downside_deviation) * math.sqrt(self.TRADING_DAYS_PER_YEAR), 4)

    def _max_drawdown(self, equity_values: list[float]) -> tuple[float, float]:
        peak = equity_values[0]
        max_drawdown_pct = 0.0
        max_drawdown_amount = 0.0
        for equity in equity_values:
            peak = max(peak, equity)
            drawdown_amount = peak - equity
            max_drawdown_amount = max(max_drawdown_amount, drawdown_amount)
            if peak > 0:
                max_drawdown_pct = max(max_drawdown_pct, (drawdown_amount / peak) * 100)
        return round(max_drawdown_pct, 2), round(max_drawdown_amount, 2)

    def _trade_pnls(self, trades: list[dict[str, Any]]) -> list[float]:
        values = []
        for trade in trades:
            try:
                values.append(float(trade.get("pnl", trade.get("net_pnl", 0.0))))
            except (TypeError, ValueError):
                values.append(0.0)
        return values

    def _profit_factor(self, trades: list[dict[str, Any]]) -> float:
        pnls = self._trade_pnls(trades)
        gross_profit = sum(value for value in pnls if value > 0)
        gross_loss = abs(sum(value for value in pnls if value < 0))
        if gross_loss == 0:
            return round(gross_profit, 4) if gross_profit else 0.0
        return round(gross_profit / gross_loss, 4)

    def _expectancy(self, trades: list[dict[str, Any]]) -> float:
        pnls = self._trade_pnls(trades)
        return round(mean(pnls), 2) if pnls else 0.0

    def _average_pnl(self, trades: list[dict[str, Any]], *, wins: bool) -> float:
        pnls = self._trade_pnls(trades)
        filtered = [value for value in pnls if value > 0] if wins else [value for value in pnls if value < 0]
        return round(mean(filtered), 2) if filtered else 0.0

    def _exposure_pct(self, trades: list[dict[str, Any]], equity_frame: pd.DataFrame) -> float:
        start = equity_frame.iloc[0]["timestamp"]
        end = equity_frame.iloc[-1]["timestamp"]
        total_seconds = max((end - start).total_seconds(), 1)
        exposed_seconds = 0.0
        for trade in trades:
            entry = pd.to_datetime(trade.get("entry_time") or trade.get("entry_date"), errors="coerce")
            exit_time = pd.to_datetime(trade.get("exit_time") or trade.get("exit_date"), errors="coerce")
            if pd.isna(entry) or pd.isna(exit_time):
                continue
            exposed_seconds += max((exit_time - entry).total_seconds(), 0)
        return round(min(100.0, (exposed_seconds / total_seconds) * 100), 2)

    def _highlights(self, metrics: dict[str, float]) -> list[dict[str, Any]]:
        checks = [
            ("Sharpe Ratio", metrics["sharpe_ratio"], metrics["sharpe_ratio"] >= 1.0),
            ("Sortino Ratio", metrics["sortino_ratio"], metrics["sortino_ratio"] >= 1.0),
            ("Profit Factor", metrics["profit_factor"], metrics["profit_factor"] >= 1.2),
            ("Expectancy", metrics["expectancy"], metrics["expectancy"] > 0),
            ("Recovery Factor", metrics["recovery_factor"], metrics["recovery_factor"] >= 1.0),
        ]
        return [{"metric": name, "value": value, "passed": passed} for name, value, passed in checks]

    def _warnings(self, metrics: dict[str, float], max_drawdown_pct: float) -> list[str]:
        warnings = []
        if metrics["sharpe_ratio"] < 1:
            warnings.append("Sharpe Ratio is below 1.0.")
        if metrics["sortino_ratio"] < 1:
            warnings.append("Sortino Ratio is below 1.0.")
        if metrics["profit_factor"] < 1.2:
            warnings.append("Profit Factor is below 1.2.")
        if metrics["expectancy"] <= 0:
            warnings.append("Expectancy is not positive.")
        if max_drawdown_pct > 25:
            warnings.append("Max drawdown is above 25%.")
        if not warnings:
            warnings.append("No major scorecard warnings from available metrics.")
        return warnings
