from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

import pandas as pd
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.exceptions import InvalidRequestError
from app.schemas.strategy_schema import StrategyDefinition


class BaseStrategyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")


ParameterModelT = TypeVar("ParameterModelT", bound=BaseStrategyParameters)


class BaseStrategy(ABC, Generic[ParameterModelT]):
    slug: str = "base"
    name: str = "Base Strategy"
    description: str = "Base strategy template."
    aliases: tuple[str, ...] = ()
    parameter_model: type[ParameterModelT] = BaseStrategyParameters

    def identifiers(self) -> tuple[str, ...]:
        return (self.slug, self.name, *self.aliases)

    def default_parameters(self) -> dict[str, Any]:
        return self.parameter_model().model_dump(mode="json")

    def definition(self) -> StrategyDefinition:
        schema = self.parameter_model.model_json_schema()
        schema.pop("title", None)
        return StrategyDefinition(
            slug=self.slug,
            name=self.name,
            description=self.description,
            aliases=list(self.aliases),
            default_parameters=self.default_parameters(),
            parameter_schema=schema,
        )

    def validate_parameters(self, parameters: dict[str, Any] | None = None) -> ParameterModelT:
        raw_parameters = parameters or {}
        if not isinstance(raw_parameters, dict):
            raise InvalidRequestError(
                f"Parameters for strategy '{self.slug}' must be provided as a JSON object"
            )

        try:
            return self.parameter_model.model_validate(raw_parameters)
        except ValidationError as exc:
            issues: list[str] = []
            for error in exc.errors(include_url=False):
                location = ".".join(str(part) for part in error.get("loc", ()))
                message = error.get("msg", "Invalid value")
                if message.startswith("Value error, "):
                    message = message.removeprefix("Value error, ")
                issues.append(f"{location}: {message}" if location else message)
            detail = "; ".join(issues) or "Invalid strategy parameters"
            raise InvalidRequestError(
                f"Invalid parameters for strategy '{self.slug}': {detail}"
            ) from exc

    def apply(self, df: pd.DataFrame, parameters: dict[str, Any] | None = None) -> pd.DataFrame:
        validated_parameters = self.validate_parameters(parameters)
        frame = self._apply(df.copy(), validated_parameters)

        for signal_column in ("buy_signal", "sell_signal"):
            if signal_column not in frame.columns:
                raise RuntimeError(
                    f"Strategy '{self.slug}' did not produce required column '{signal_column}'"
                )
            frame[signal_column] = frame[signal_column].fillna(False).astype(bool)

        return frame

    @abstractmethod
    def _apply(self, df: pd.DataFrame, parameters: ParameterModelT) -> pd.DataFrame:
        raise NotImplementedError
