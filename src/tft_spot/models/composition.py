from typing import Literal

from pydantic import Field, model_validator

from tft_spot.models.configuration import (
    ApiModel,
    CompositionConfiguration,
    PriorityDecision,
    ScoringWeights,
    UnitPriorityDecision,
)


class ComponentDemand(PriorityDecision):
    required_count: int = Field(ge=1, strict=True)


class EngineComposition(ApiModel):
    source_id: str = Field(min_length=1)
    set_number: int = Field(ge=1)
    status: Literal["ready"]
    title: str
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    units: list[UnitPriorityDecision]
    components: list[ComponentDemand]
    augments: list[PriorityDecision]

    @model_validator(mode="after")
    def validate_decisions(self) -> EngineComposition:
        CompositionConfiguration.model_validate(self.model_dump())
        return self
