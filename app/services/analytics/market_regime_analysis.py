from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.exceptions import InvalidRequestError


class MarketRegimeAnalysis:
    REGIMES = ("Bull trend", "Bear trend", "Sideways")

    def run(
        self,
        *,
        market_data: list[dict[str, Any]],
        trades: list[dict[str, Any]],
        initial_capital: float,
        slope_threshold_pct: float = 0.1,
    ) -> dict[str, Any]:
        if initial_capital <= 0:
            raise InvalidRequestError("initial_capital must be greater than zero")
        if not market_data:
            raise InvalidRequestError("Market regime analysis requires market data from a backtest")

        regime_frame = self._classify_market_data(market_data, slope_threshold_pct)
        trade_rows = self._assign_trades_to_regimes(trades, regime_frame)
        breakdown = [self._regime_metrics(regime, trade_rows.get(regime, []), initial_capital) for regime in self.REGIMES]

        best = max(breakdown, key=lambda item: item["return_pct"])
        worst = min(breakdown, key=lambda item: item["return_pct"])
        return {
            "method": (
                "V1 classifies each bar using a 20-period moving average slope over 5 bars. "
                "Positive slope above the threshold is Bull trend, negative slope below the threshold is Bear trend, "
                "and low-slope or mixed bars are Sideways."
            ),
            "slope_threshold_pct": slope_threshold_pct,
            "regime_counts": self._regime_counts(regime_frame),
            "breakdown": breakdown,
            "best_regime": best["regime"],
            "worst_regime": worst["regime"],
            "robustness_summary": self._robustness_summary(breakdown),
        }

    def _classify_market_data(self, market_data: list[dict[str, Any]], slope_threshold_pct: float) -> pd.DataFrame:
        frame = pd.DataFrame(market_data)
        if "timestamp" not in frame.columns or "close" not in frame.columns:
            raise InvalidRequestError("market_data must include timestamp and close values")

        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["timestamp", "close"]).sort_values("timestamp").reset_index(drop=True)
        if frame.empty:
            raise InvalidRequestError("market_data does not contain valid timestamp and close values")

        window = min(20, max(3, len(frame)))
        slope_period = min(5, max(1, len(frame) - 1))
        frame["moving_average"] = frame["close"].rolling(window=window, min_periods=1).mean()
        frame["ma_slope_pct"] = frame["moving_average"].pct_change(periods=slope_period).fillna(0) * 100
        frame["regime"] = frame.apply(
            lambda row: self._classify_bar(row["close"], row["moving_average"], row["ma_slope_pct"], slope_threshold_pct),
            axis=1,
        )
        return frame

    def _classify_bar(self, close: float, moving_average: float, slope_pct: float, slope_threshold_pct: float) -> str:
        if slope_pct > slope_threshold_pct and close >= moving_average:
            return "Bull trend"
        if slope_pct < -slope_threshold_pct and close <= moving_average:
            return "Bear trend"
        return "Sideways"

    def _assign_trades_to_regimes(
        self,
        trades: list[dict[str, Any]],
        regime_frame: pd.DataFrame,
    ) -> dict[str, list[dict[str, Any]]]:
        grouped = {regime: [] for regime in self.REGIMES}
        if not trades:
            return grouped

        lookup = regime_frame[["timestamp", "regime"]].copy()
        for trade in trades:
            exit_time = pd.to_datetime(trade.get("exit_time") or trade.get("exit_date"), errors="coerce")
            if pd.isna(exit_time):
                regime = "Sideways"
            else:
                index = lookup["timestamp"].searchsorted(exit_time, side="right") - 1
                regime = str(lookup.iloc[index]["regime"]) if index >= 0 else "Sideways"
            grouped.setdefault(regime, []).append(trade)
        return grouped

    def _regime_metrics(self, regime: str, trades: list[dict[str, Any]], initial_capital: float) -> dict[str, Any]:
        pnl_values = [self._trade_pnl(trade) for trade in trades]
        net_profit = sum(pnl_values)
        trades_count = len(pnl_values)
        wins = sum(1 for value in pnl_values if value > 0)
        return_pct = (net_profit / initial_capital) * 100 if initial_capital else 0.0
        return {
            "regime": regime,
            "return_pct": round(return_pct, 2),
            "net_profit": round(net_profit, 2),
            "win_rate_pct": round((wins / trades_count) * 100, 2) if trades_count else 0.0,
            "drawdown_pct": self._trade_drawdown_pct(pnl_values, initial_capital),
            "trades_count": trades_count,
        }

    def _trade_pnl(self, trade: dict[str, Any]) -> float:
        try:
            return float(trade.get("pnl", trade.get("net_pnl", 0.0)))
        except (TypeError, ValueError):
            return 0.0

    def _trade_drawdown_pct(self, pnl_values: list[float], initial_capital: float) -> float:
        equity = initial_capital
        peak = initial_capital
        max_drawdown = 0.0
        for pnl in pnl_values:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, ((peak - equity) / peak) * 100)
        return round(max_drawdown, 2)

    def _regime_counts(self, regime_frame: pd.DataFrame) -> dict[str, int]:
        counts = regime_frame["regime"].value_counts().to_dict()
        return {regime: int(counts.get(regime, 0)) for regime in self.REGIMES}

    def _robustness_summary(self, breakdown: list[dict[str, Any]]) -> dict[str, Any]:
        active = [item for item in breakdown if item["trades_count"] > 0]
        if not active:
            return {
                "profitable_regimes": 0,
                "active_regimes": 0,
                "return_spread_pct": 0.0,
                "robustness_score": 0.0,
                "summary": "No completed trades were available for regime scoring.",
            }

        profitable = sum(1 for item in active if item["return_pct"] > 0)
        returns = [item["return_pct"] for item in active]
        spread = max(returns) - min(returns)
        score = (profitable / len(active)) * 100
        score -= min(40.0, spread * 2)
        score = round(max(0.0, min(100.0, score)), 2)
        return {
            "profitable_regimes": profitable,
            "active_regimes": len(active),
            "return_spread_pct": round(spread, 2),
            "robustness_score": score,
            "summary": f"Profitable in {profitable} of {len(active)} active regimes with {round(spread, 2)}% return spread.",
        }
