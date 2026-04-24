from __future__ import annotations

import random
from statistics import median
from typing import Any

from app.core.exceptions import InvalidRequestError


class MonteCarloAnalysis:
    def run(
        self,
        *,
        trades: list[dict[str, Any]],
        initial_capital: float,
        simulation_count: int,
        drawdown_threshold_pct: float,
        noise_pct: float = 5.0,
        seed: int | None = None,
    ) -> dict[str, Any]:
        if simulation_count not in {100, 500, 1000}:
            raise InvalidRequestError("simulation_count must be one of 100, 500, or 1000")
        if initial_capital <= 0:
            raise InvalidRequestError("initial_capital must be greater than zero")
        if drawdown_threshold_pct < 0:
            raise InvalidRequestError("drawdown_threshold_pct must be zero or greater")

        pnl_values = [self._trade_pnl(trade) for trade in trades]
        if not pnl_values:
            raise InvalidRequestError("Monte Carlo analysis requires at least one completed trade")

        rng = random.Random(seed)
        simulations: list[dict[str, Any]] = []

        for index in range(simulation_count):
            shuffled = pnl_values.copy()
            rng.shuffle(shuffled)
            perturbed = [self._perturb_pnl(value, noise_pct, rng) for value in shuffled]
            result = self._simulate_path(perturbed, initial_capital)
            result["simulation"] = index + 1
            simulations.append(result)

        returns = [item["total_return_pct"] for item in simulations]
        drawdowns = [item["max_drawdown_pct"] for item in simulations]
        loss_count = sum(1 for value in returns if value < 0)
        threshold_count = sum(1 for value in drawdowns if value > drawdown_threshold_pct)
        median_return = round(float(median(returns)), 2)
        worst_return = round(min(returns), 2)
        best_return = round(max(returns), 2)
        probability_of_loss = round((loss_count / simulation_count) * 100, 2)
        probability_drawdown_beyond_threshold = round((threshold_count / simulation_count) * 100, 2)

        return {
            "simulation_count": simulation_count,
            "trade_count": len(pnl_values),
            "initial_capital": round(initial_capital, 2),
            "drawdown_threshold_pct": drawdown_threshold_pct,
            "noise_pct": noise_pct,
            "median_return": median_return,
            "worst_case_return": worst_return,
            "best_case_return": best_return,
            "probability_of_loss": probability_of_loss,
            "probability_of_drawdown_beyond_threshold": probability_drawdown_beyond_threshold,
            "robustness_score": self._robustness_score(
                median_return,
                worst_return,
                probability_of_loss,
                probability_drawdown_beyond_threshold,
            ),
            "distribution": self._distribution_buckets(returns),
            "sample_simulations": simulations[: min(50, len(simulations))],
        }

    def _trade_pnl(self, trade: dict[str, Any]) -> float:
        value = trade.get("pnl", trade.get("net_pnl"))
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError("Each trade must include a numeric pnl value") from exc

    def _perturb_pnl(self, pnl: float, noise_pct: float, rng: random.Random) -> float:
        noise_fraction = max(0.0, noise_pct) / 100
        if noise_fraction == 0:
            return pnl
        return pnl + (abs(pnl) * rng.uniform(-noise_fraction, noise_fraction))

    def _simulate_path(self, pnl_values: list[float], initial_capital: float) -> dict[str, Any]:
        equity = initial_capital
        peak_equity = initial_capital
        max_drawdown = 0.0

        for pnl in pnl_values:
            equity += pnl
            peak_equity = max(peak_equity, equity)
            if peak_equity > 0:
                drawdown = ((peak_equity - equity) / peak_equity) * 100
                max_drawdown = max(max_drawdown, drawdown)

        net_profit = equity - initial_capital
        total_return = (net_profit / initial_capital) * 100 if initial_capital else 0.0
        return {
            "ending_equity": round(equity, 2),
            "net_profit": round(net_profit, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
        }

    def _robustness_score(
        self,
        median_return: float,
        worst_return: float,
        probability_of_loss: float,
        probability_drawdown_beyond_threshold: float,
    ) -> float:
        score = 100.0
        score -= max(0.0, probability_of_loss * 0.6)
        score -= max(0.0, probability_drawdown_beyond_threshold * 0.4)
        if median_return < 0:
            score += median_return
        if worst_return < 0:
            score += worst_return * 0.25
        return round(max(0.0, min(100.0, score)), 2)

    def _distribution_buckets(self, returns: list[float]) -> list[dict[str, Any]]:
        if not returns:
            return []

        minimum = min(returns)
        maximum = max(returns)
        if minimum == maximum:
            return [{"label": f"{round(minimum, 2)}%", "min": round(minimum, 2), "max": round(maximum, 2), "count": len(returns)}]

        bucket_count = 10
        width = (maximum - minimum) / bucket_count
        buckets = []
        for index in range(bucket_count):
            low = minimum + (width * index)
            high = maximum if index == bucket_count - 1 else low + width
            count = sum(1 for value in returns if low <= value <= high) if index == bucket_count - 1 else sum(
                1 for value in returns if low <= value < high
            )
            buckets.append(
                {
                    "label": f"{round(low, 1)}% to {round(high, 1)}%",
                    "min": round(low, 2),
                    "max": round(high, 2),
                    "count": count,
                }
            )
        return buckets
