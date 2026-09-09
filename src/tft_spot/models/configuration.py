from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


Priority = Literal["unset", "essential", "high", "medium", "low", "avoid"]
ConfigurationStatus = Literal["draft", "ready"]


class ScoringWeights(ApiModel):
    units: int = Field(default=40, ge=0, le=100)
    components: int = Field(default=30, ge=0, le=100)
    augments: int = Field(default=30, ge=0, le=100)

    @model_validator(mode="after")
    def require_full_distribution(self) -> ScoringWeights:
        if self.units + self.components + self.augments != 100:
            raise ValueError("Scoring weights must add up to 100")
        return self


class PriorityDecision(ApiModel):
    api_name: str = Field(min_length=1)
    priority: Priority = "unset"


class UnitPriorityDecision(PriorityDecision):
    # Legacy field accepted for saved configurations; unit scoring uses core only.
    priority: Priority = "medium"
    core: bool = False


class OpenerVariant(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    units: list[UnitPriorityDecision] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_units(self):
        if len({u.api_name for u in self.units}) != len(self.units):
            raise ValueError("Duplicate opener units")
        return self


class ItemOverride(ApiModel):
    champion_api_name: str
    item_api_name: str
    fit: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=500)


class AugmentCondition(ApiModel):
    augment_api_name: str
    champion_api_name: str
    min_copies: int = Field(default=2, ge=1, le=4)
    item_api_name: str | None = None
    bonus: float = Field(default=10, ge=-20, le=20)
    reason: str = Field(min_length=1, max_length=500)


class StrategySettings(ApiModel):
    openers: list[OpenerVariant] = Field(default_factory=list, max_length=8)
    item_overrides: list[ItemOverride] = Field(default_factory=list, max_length=100)
    augment_conditions: list[AugmentCondition] = Field(
        default_factory=list, max_length=30
    )

    @model_validator(mode="after")
    def unique_entries(self):
        if len({o.name for o in self.openers}) != len(self.openers):
            raise ValueError("Duplicate opener names")
        pairs = [(o.champion_api_name, o.item_api_name) for o in self.item_overrides]
        if len(set(pairs)) != len(pairs):
            raise ValueError("Duplicate item overrides")
        return self


class CompositionConfiguration(ApiModel):
    schema_version: Literal[1] = 1
    source_id: str = Field(min_length=1)
    set_number: int = Field(ge=1)
    status: ConfigurationStatus = "draft"
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    units: list[UnitPriorityDecision] = Field(default_factory=list)
    components: list[PriorityDecision]
    augments: list[PriorityDecision]
    strategy: StrategySettings = Field(default_factory=StrategySettings)
    notes: str = ""
    updated_at: datetime | None = None

    @model_validator(mode="after")
    def require_complete_ready_configuration(self) -> CompositionConfiguration:
        for decisions in (self.units, self.components, self.augments):
            names = [decision.api_name for decision in decisions]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate priority decisions are not allowed")
        if sum(d.priority == "essential" for d in self.augments) > 1:
            raise ValueError("At most one essential augment is allowed")
        if self.status != "ready":
            return self
        if any(
            decision.priority == "unset"
            for decision in [*self.components, *self.augments]
        ):
            raise ValueError("Ready configuration cannot contain unset decisions")
        return self
