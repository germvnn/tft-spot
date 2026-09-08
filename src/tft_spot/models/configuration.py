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


class CompositionConfiguration(ApiModel):
    schema_version: Literal[1] = 1
    source_id: str = Field(min_length=1)
    set_number: int = Field(ge=1)
    status: ConfigurationStatus = "draft"
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    units: list[UnitPriorityDecision] = Field(default_factory=list)
    components: list[PriorityDecision]
    augments: list[PriorityDecision]
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
