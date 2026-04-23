from __future__ import annotations

from itertools import product
from math import isfinite
from typing import Any

from app.core.exceptions import InvalidRequestError
from app.schemas.backtest_schema import BacktestRunRequest
from app.services.analytics.metrics_service import MetricsService
from app.services.backtesting.engine import BacktestEngine
from app.services.data.data_loader_service import DataLoaderService
from app.services.strategies.strategy_registry import StrategyRegistry


class ParameterOptimizer:
    DEFAULT_MAX_RESULTS = 20

    def __init__(self) -> None:
        self.loader = DataLoaderService()
        self.registry = StrategyRegistry()
        self.engine = BacktestEngine()
        self.metrics = MetricsService()

    def optimize(self, payload: BacktestRunRequest, *, max_results: int = DEFAULT_MAX_RESULTS) -> dict:
        strategy = self.registry.get(payload.strategy_name)
        frame = self.loader.load(payload.source, payload.file_name)
        parameter_grid = self._build_parameter_grid(
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

            signal_frame = strategy.apply(frame, validated_parameters)
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
            evaluated_count += 1
            ranked_results.append(
                {
                    "strategy_name": strategy.slug,
                    "symbol": payload.symbol,
                    "timeframe": payload.timeframe,
                    "parameters": validated_parameters,
                    "score": metrics["total_return_pct"],
                    "objective_score": metrics["total_return_pct"],
                    "total_return_pct": metrics["total_return_pct"],
                    "win_rate_pct": metrics["win_rate_pct"],
                    "max_drawdown_pct": metrics["max_drawdown_pct"],
                    "metrics": metrics,
                }
            )

        ranked_results.sort(
            key=lambda item: (
                self._safe_number(item.get("score")),
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
            "evaluated_count": evaluated_count,
            "results": limited_results,
        }

    def _build_parameter_grid(
        self,
        parameter_schema: dict[str, Any] | None,
        current_parameters: dict[str, Any] | None,
    ) -> dict[str, list[Any]]:
        properties = (parameter_schema or {}).get("properties") or {}
        normalized_parameters = current_parameters or {}
        parameter_grid: dict[str, list[Any]] = {}

        for name, schema in properties.items():
            value = normalized_parameters.get(name, schema.get("default"))
            parameter_grid[name] = self._build_parameter_candidates(name, value, schema)

        return parameter_grid

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
