from pydantic import ConfigDict, Field, model_validator

from tft_spot.models.configuration import ApiModel


class OwnedUnit(ApiModel):
    model_config = ConfigDict(extra="forbid")

    api_name: str = Field(min_length=1)
    stars: int = Field(default=1, ge=1, le=3, strict=True)
    count: int = Field(default=1, ge=1, le=99, strict=True)


class OwnedComponent(ApiModel):
    model_config = ConfigDict(extra="forbid")

    api_name: str = Field(min_length=1)
    count: int = Field(default=1, ge=1, le=99, strict=True)


class Spot(ApiModel):
    model_config = ConfigDict(extra="forbid")

    set_number: int = Field(ge=1, strict=True)
    offered_augments: list[str] = Field(min_length=1, max_length=3)
    units: list[OwnedUnit] = Field(default_factory=list)
    components: list[OwnedComponent] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_offer(self) -> Spot:
        if any(not name for name in self.offered_augments):
            raise ValueError("Augment apiName must not be empty")
        if len(set(self.offered_augments)) != len(self.offered_augments):
            raise ValueError("Offered augments must be unique")
        return self
