from __future__ import annotations

from itertools import product
from math import isfinite
from typing import Any

from app.core.exceptions import InvalidRequestError
from app.schemas.backtest_schema import BacktestRunRequest
from app.services.analytics.metrics_service import MetricsService
from app.services.backtesting.engine import BacktestEngine
from app.services.data.date_range_filter_service import DateRangeFilterService
from app.services.data.data_loader_service import DataLoaderService
from app.services.strategies.strategy_registry import StrategyRegistry


class ParameterOptimizer:
    DEFAULT_MAX_RESULTS = 20
    WALK_FORWARD_SPLITS = {
        "70_30": 0.70,
        "60_40": 0.60,
    }

    def __init__(self) -> None:
        self.loader = DataLoaderService()
        self.date_filter = DateRangeFilterService()
        self.registry = StrategyRegistry()
        self.engine = BacktestEngine()
        self.metrics = MetricsService()

    def optimize(self, payload: BacktestRunRequest, *, max_results: int = DEFAULT_MAX_RESULTS) -> dict:
        optimization_mode = getattr(payload, "optimization_mode", "standard") or "standard"
        if optimization_mode == "walk_forward":
            return self.optimize_walk_forward(payload, max_results=max_results)

        strategy = self.registry.get(payload.strategy_name)
        frame = self.loader.load(payload.source, payload.file_name)
        frame = self.date_filter.filter(frame, payload.from_date, payload.to_date)
        ranking_metric = getattr(payload, "ranking_metric", "net_profit") or "net_profit"
        parameter_grid = self._build_parameter_grid(
            strategy.slug,
            strategy.definition().parameter_schema,
            payload.parameters or strategy.default_parameters(),
        )

        ranked_results: list[dict[str, Any]] = []
        evaluated_count = 0

        for candidate_parameters in self._iter_parameter_sets(parameter_grid):
            try:
                validated_parameters = strategy.validate_parameters(candidate_parameters).model_dump(mode="json")
            except InvalidRequestError:
                continue

            evaluation = self._evaluate_candidate(frame, strategy, validated_parameters, payload)
            metrics = evaluation["metrics"]
            evaluated_count += 1
            ranked_results.append(
                {
                    "strategy_name": strategy.slug,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                    "from_date": payload.from_date,
                    "to_date": payload.to_date,
                    "parameters": validated_parameters,
                    "score": self._ranking_score(metrics, ranking_metric),
                    "objective_score": self._ranking_score(metrics, ranking_metric),
                    "ranking_metric": ranking_metric,
                    "net_profit": metrics["net_profit"],
                    "total_return_pct": metrics["total_return_pct"],
                    "win_rate_pct": metrics["win_rate_pct"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                    "total_trades": metrics["total_trades"],
                    "ending_equity": metrics["ending_equity"],
                    "metrics": metrics,
                    "trades": evaluation["trades"],
                }
            )

        ranked_results.sort(
            key=lambda item: (
                self._safe_number(item.get("score")),
                self._safe_number(item.get("net_profit")),
                self._safe_number(item.get("win_rate_pct")),
                -self._safe_number(item.get("max_drawdown_pct")),
            ),
            reverse=True,
        )

        limited_results = ranked_results[: max(1, max_results)]
        for index, result in enumerate(limited_results, start=1):
            result["rank"] = index

        return {
            "strategy_name": strategy.slug,
            "ranking_metric": ranking_metric,
            "evaluated_count": evaluated_count,
            "results": limited_results,
        }

    def optimize_walk_forward(self, payload: BacktestRunRequest, *, max_results: int = DEFAULT_MAX_RESULTS) -> dict:
        strategy = self.registry.get(payload.strategy_name)
        frame = self.loader.load(payload.source, payload.file_name)
        frame = self.date_filter.filter(frame, payload.from_date, payload.to_date)
        frame = self._chronological_frame(frame)

        split_key = getattr(payload, "walk_forward_split", "70_30") or "70_30"
        split_ratio = self.WALK_FORWARD_SPLITS.get(split_key, self.WALK_FORWARD_SPLITS["70_30"])
        in_sample_frame, out_sample_frame = self._split_frame(frame, split_ratio)
        ranking_metric = getattr(payload, "ranking_metric", "net_profit") or "net_profit"

        parameter_grid = self._build_parameter_grid(
            strategy.slug,
            strategy.definition().parameter_schema,
            payload.parameters or strategy.default_parameters(),
        )

        evaluated_results: list[dict[str, Any]] = []
        evaluated_count = 0

        for candidate_parameters in self._iter_parameter_sets(parameter_grid):
            try:
                validated_parameters = strategy.validate_parameters(candidate_parameters).model_dump(mode="json")
            except InvalidRequestError:
                continue

            in_evaluation = self._evaluate_candidate(in_sample_frame, strategy, validated_parameters, payload)
            out_evaluation = self._evaluate_candidate(out_sample_frame, strategy, validated_parameters, payload)
            in_metrics = in_evaluation["metrics"]
            out_metrics = out_evaluation["metrics"]
            evaluated_count += 1

            in_profit = self._safe_number(in_metrics.get("net_profit"))
            out_profit = self._safe_number(out_metrics.get("net_profit"))
            in_return = self._safe_number(in_metrics.get("total_return_pct"))
            out_return = self._safe_number(out_metrics.get("total_return_pct"))
            out_drawdown = self._safe_number(out_metrics.get("max_drawdown_pct"))
            degradation_pct = self._degradation_pct(in_profit, out_profit)
            robustness_score = self._robustness_score(in_profit, out_profit, out_drawdown)
            performance_degraded = self._performance_degraded(in_profit, out_profit, in_return, out_return)

            evaluated_results.append(
                {
                    "strategy_name": strategy.slug,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                    "from_date": payload.from_date,
                    "to_date": payload.to_date,
                    "parameters": validated_parameters,
                    "optimization_mode": "walk_forward",
                    "walk_forward_split": split_key,
                    "in_sample_rows": len(in_sample_frame),
                    "out_sample_rows": len(out_sample_frame),
                    "in_sample_score": self._ranking_score(in_metrics, ranking_metric),
                    "score": out_profit,
                    "objective_score": out_profit,
                    "ranking_metric": "out_sample_net_profit",
                    "in_sample_ranking_metric": ranking_metric,
                    "in_sample_net_profit": in_metrics["net_profit"],
                    "out_sample_net_profit": out_metrics["net_profit"],
                    "in_sample_return": in_metrics["total_return_pct"],
                    "out_sample_return": out_metrics["total_return_pct"],
                    "out_sample_drawdown": out_metrics["max_drawdown_pct"],
                    "robustness_score": robustness_score,
                    "degradation_pct": degradation_pct,
                    "performance_degraded": performance_degraded,
                    "degradation_label": "Significant" if performance_degraded else "Contained",
                    "net_profit": out_metrics["net_profit"],
                    "total_return_pct": out_metrics["total_return_pct"],
                    "win_rate_pct": out_metrics["win_rate_pct"],
                    "max_drawdown_pct": out_metrics["max_drawdown_pct"],
                    "total_trades": out_metrics["total_trades"],
                    "ending_equity": out_metrics["ending_equity"],
                    "in_sample_metrics": in_metrics,
                    "out_sample_metrics": out_metrics,
                    "metrics": out_metrics,
                    "in_sample_trades": in_evaluation["trades"],
                    "out_sample_trades": out_evaluation["trades"],
                    "trades": out_evaluation["trades"],
                }
            )

        in_sample_ranked = sorted(
            evaluated_results,
            key=lambda item: (
                self._safe_number(item.get("in_sample_score")),
                self._safe_number(item.get("in_sample_net_profit")),
                -self._safe_number(item.get("out_sample_drawdown")),
            ),
            reverse=True,
        )
        for index, result in enumerate(in_sample_ranked, start=1):
            result["in_sample_rank"] = index

        evaluated_results.sort(
            key=lambda item: (
                self._safe_number(item.get("out_sample_net_profit")),
                self._safe_number(item.get("out_sample_return")),
                self._safe_number(item.get("robustness_score")),
                -self._safe_number(item.get("out_sample_drawdown")),
            ),
            reverse=True,
        )

        limited_results = evaluated_results[: max(1, max_results)]
        for index, result in enumerate(limited_results, start=1):
            result["rank"] = index

        best_in_sample = in_sample_ranked[0] if in_sample_ranked else None
        return {
            "strategy_name": strategy.slug,
            "optimization_mode": "walk_forward",
            "walk_forward_split": split_key,
            "split_ratio": split_ratio,
            "ranking_metric": "out_sample_net_profit",
            "in_sample_ranking_metric": ranking_metric,
            "evaluated_count": evaluated_count,
            "best_in_sample_parameters": best_in_sample["parameters"] if best_in_sample else {},
            "best_in_sample": best_in_sample,
            "results": limited_results,
        }

    def _evaluate_candidate(
        self,
        frame,
        strategy,
        parameters: dict[str, Any],
        payload: BacktestRunRequest,
    ) -> dict[str, Any]:
        signal_frame = strategy.apply(frame, parameters)
        raw_result = self.engine.run(
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
        metrics = self.metrics.calculate(
            payload.initial_capital,
            raw_result["ending_equity"],
            raw_result["trades"],
            raw_result["equity_curve"],
        )
        return {
            "metrics": metrics,
            "trades": raw_result["trades"],
            "equity_curve": raw_result["equity_curve"],
            "ending_equity": raw_result["ending_equity"],
        }

    def _chronological_frame(self, frame):
        if "Date" not in frame.columns:
            return frame.reset_index(drop=True)
        return frame.sort_values("Date").reset_index(drop=True)

    def _split_frame(self, frame, split_ratio: float):
        if len(frame) < 2:
            raise InvalidRequestError("Walk-forward optimization requires at least two rows of market data")
        split_index = round(len(frame) * split_ratio)
        split_index = max(1, min(len(frame) - 1, split_index))
        return frame.iloc[:split_index].reset_index(drop=True), frame.iloc[split_index:].reset_index(drop=True)

    def _degradation_pct(self, in_sample_net_profit: float, out_sample_net_profit: float) -> float:
        if not isfinite(in_sample_net_profit) or abs(in_sample_net_profit) < 0.000001:
            return 0.0 if out_sample_net_profit >= 0 else 100.0
        degradation = ((in_sample_net_profit - out_sample_net_profit) / abs(in_sample_net_profit)) * 100
        return round(max(0.0, degradation), 2)

    def _robustness_score(
        self,
        in_sample_net_profit: float,
        out_sample_net_profit: float,
        out_sample_drawdown: float,
    ) -> float:
        if not isfinite(in_sample_net_profit) or not isfinite(out_sample_net_profit):
            return 0.0
        if in_sample_net_profit <= 0:
            base_score = 100.0 if out_sample_net_profit > 0 else 0.0
        else:
            base_score = max(0.0, min(100.0, (out_sample_net_profit / in_sample_net_profit) * 100))
        drawdown_penalty = max(0.0, min(25.0, out_sample_drawdown * 0.25 if isfinite(out_sample_drawdown) else 0.0))
        return round(max(0.0, base_score - drawdown_penalty), 2)

    def _performance_degraded(
        self,
        in_sample_net_profit: float,
        out_sample_net_profit: float,
        in_sample_return: float,
        out_sample_return: float,
    ) -> bool:
        if in_sample_net_profit > 0 and out_sample_net_profit < 0:
            return True
        if in_sample_return > 0 and out_sample_return < 0:
            return True
        if in_sample_net_profit > 0 and out_sample_net_profit < (in_sample_net_profit * 0.5):
            return True
        return False

    def _build_parameter_grid(
        self,
        strategy_slug: str,
        parameter_schema: dict[str, Any] | None,
        current_parameters: dict[str, Any] | None,
    ) -> dict[str, list[Any]]:
        properties = (parameter_schema or {}).get("properties") or {}
        normalized_parameters = current_parameters or {}
        parameter_grid: dict[str, list[Any]] = {}

        for name, schema in properties.items():
            value = normalized_parameters.get(name, schema.get("default"))
            if not isinstance(value, (list, tuple, set)):
                value = self._default_candidates_for_strategy(strategy_slug, name, value)
            parameter_grid[name] = self._build_parameter_candidates(name, value, schema)

        return parameter_grid

    def _default_candidates_for_strategy(self, strategy_slug: str, name: str, value: Any) -> Any:
        defaults: dict[str, dict[str, list[Any]]] = {
            "ema_crossover": {
                "fast_period": [5, 10, 15, 20],
                "slow_period": [30, 50, 100, 150, 200],
            },
            "trend_following": {
                "fast_period": [5, 10, 15, 20],
                "slow_period": [30, 50, 100, 150, 200],
            },
            "intraday": {
                "fast_period": [5, 10, 15, 20],
                "slow_period": [30, 50, 100, 150, 200],
            },
            "positional": {
                "fast_period": [5, 10, 15, 20],
                "slow_period": [30, 50, 100, 150, 200],
            },
            "rsi_reversal": {
                "rsi_period": [7, 14, 21],
                "oversold": [20, 25, 30, 35],
                "overbought": [60, 65, 70, 75, 80],
            },
            "mean_reversion": {
                "rsi_period": [7, 14, 21],
                "oversold": [20, 25, 30, 35],
                "overbought": [60, 65, 70, 75, 80],
            },
        }
        return defaults.get(strategy_slug, {}).get(name, value)

    def _build_parameter_candidates(self, name: str, value: Any, schema: dict[str, Any]) -> list[Any]:
        if isinstance(value, (list, tuple, set)):
            return self._explicit_candidates(name, list(value), schema)

        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and enum_values:
            return self._unique_preserving_order([value, *enum_values])

        schema_type = schema.get("type")
        if schema_type in {"integer", "number"}:
            return self._numeric_candidates(value, schema, is_integer=schema_type == "integer")

        fallback = schema.get("default", value)
        return [fallback] if fallback is not None else []

    def _explicit_candidates(self, name: str, values: list[Any], schema: dict[str, Any]) -> list[Any]:
        label = schema.get("title") or name
        if not values:
            raise InvalidRequestError(f"Optimization values for '{label}' cannot be empty")

        schema_type = schema.get("type")
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        normalized_values: list[Any] = []

        for raw_value in values:
            if schema_type == "integer":
                numeric_value = self._coerce_numeric_candidate(raw_value, label)
                if not float(numeric_value).is_integer():
                    raise InvalidRequestError(f"Optimization values for '{label}' must be whole numbers")
                candidate = int(round(numeric_value))
            elif schema_type == "number":
                candidate = round(float(self._coerce_numeric_candidate(raw_value, label)), 4)
            else:
                candidate = raw_value

            if minimum is not None and candidate < minimum:
                raise InvalidRequestError(f"Optimization values for '{label}' must be at least {minimum}")
            if maximum is not None and candidate > maximum:
                raise InvalidRequestError(f"Optimization values for '{label}' must be at most {maximum}")

            normalized_values.append(candidate)

        return self._unique_preserving_order(normalized_values)

    def _coerce_numeric_candidate(self, raw_value: Any, label: str) -> float:
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise InvalidRequestError(f"Optimization values for '{label}' must be numeric") from exc

        if not isfinite(value):
            raise InvalidRequestError(f"Optimization values for '{label}' must be finite numbers")
        return value

    def _numeric_candidates(self, value: Any, schema: dict[str, Any], *, is_integer: bool) -> list[Any]:
        default_value = schema.get("default", value)
        if default_value is None:
            return []

        base_value = int(default_value) if is_integer else float(default_value)
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        step = self._numeric_step(base_value, minimum, maximum, is_integer=is_integer)

        candidates = [base_value - step, base_value, base_value + step]
        normalized_candidates: list[Any] = []

        for candidate in candidates:
            if minimum is not None:
                candidate = max(candidate, minimum)
            if maximum is not None:
                candidate = min(candidate, maximum)
            if is_integer:
                normalized_candidates.append(int(round(candidate)))
            else:
                normalized_candidates.append(round(float(candidate), 4))

        return self._unique_preserving_order(normalized_candidates)

    def _numeric_step(
        self,
        base_value: float,
        minimum: Any,
        maximum: Any,
        *,
        is_integer: bool,
    ) -> float:
        if self._is_finite_number(minimum) and self._is_finite_number(maximum) and float(maximum) > float(minimum):
            spread = (float(maximum) - float(minimum)) / 4
            if is_integer:
                return max(1, round(spread))
            return max(spread, 0.5)

        magnitude = abs(float(base_value))
        if is_integer:
            return max(1, round(magnitude * 0.25))
        return max(magnitude * 0.25, 0.5)

    def _iter_parameter_sets(self, parameter_grid: dict[str, list[Any]]):
        if not parameter_grid:
            yield {}
            return

        parameter_names = list(parameter_grid)
        for values in product(*(parameter_grid[name] for name in parameter_names)):
            yield dict(zip(parameter_names, values))

    def _unique_preserving_order(self, values: list[Any]) -> list[Any]:
        unique_values: list[Any] = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)
        return unique_values

    def _is_finite_number(self, value: Any) -> bool:
        if value is None:
            return False
        try:
            return isfinite(float(value))
        except (TypeError, ValueError):
            return False

    def _safe_number(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("-inf")

    def _ranking_score(self, metrics: dict[str, Any], ranking_metric: str) -> float:
        value = self._safe_number(metrics.get(ranking_metric))
        if ranking_metric == "max_drawdown_pct":
            return -value
        return value
