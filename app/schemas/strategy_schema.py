from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

class StrategyDefinition(BaseModel):
    slug: str
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    default_parameters: dict[str, Any] = Field(default_factory=dict)
    parameter_schema: dict[str, Any] = Field(default_factory=dict)

class SaveStrategyRequest(BaseModel):
    name: str
    slug: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class SaveStrategyConfigurationRequest(BaseModel):
    strategy_name: str
    display_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class SavedStrategyConfigurationEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_name: str
    display_name: str
    parameters_json: str
    created_at: datetime
