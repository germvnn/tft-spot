"""Validation and explicit retirement of curated expert rules."""

from typing import Literal

from tft_spot.models.configuration import (
    CompositionConfiguration,
    RetiredStrategyRule,
    StrategySettings,
)


def validate_strategy(config: CompositionConfiguration, catalogs: dict) -> None:
    def require(category, name):
        entity = catalogs[category].get(name)
        if entity is None or entity.get("set") != config.set_number:
            raise ValueError(f"Unknown or wrong-set {category} apiName: {name}")
        return entity

    for opener in config.strategy.openers:
        for unit in opener.units:
            if require("champions", unit.api_name).get("cost") not in (1, 2, 3):
                raise ValueError("Alternative openers require cost 1-3 units")
    for override in config.strategy.item_overrides:
        require("champions", override.champion_api_name)
        if require("items", override.item_api_name).get("type") != "craftables":
            raise ValueError("Item overrides require craftable items")
    listed = {a.api_name for a in config.augments}
    for rule in config.strategy.augment_conditions:
        require("augments", rule.augment_api_name)
        if rule.augment_api_name not in listed:
            raise ValueError("Augment conditions require a listed augment")
        require("champions", rule.champion_api_name)
        if (
            rule.item_api_name
            and require("items", rule.item_api_name).get("type") != "craftables"
        ):
            raise ValueError("Augment conditions require craftable items")


def reconcile_strategy(
    config: CompositionConfiguration, catalogs: dict
) -> tuple[StrategySettings, list[RetiredStrategyRule]]:
    """Keep valid rules unchanged and archive invalid rules for human review."""
    kept: dict[Literal["openers", "item_overrides", "augment_conditions"], list] = {
        "openers": [],
        "item_overrides": [],
        "augment_conditions": [],
    }
    retired: list[RetiredStrategyRule] = []
    for field, rules in kept.items():
        for rule in getattr(config.strategy, field):
            candidate = config.model_copy(
                update={"strategy": StrategySettings(**{field: [rule]})}
            )
            try:
                validate_strategy(candidate, catalogs)
            except ValueError as error:
                retired.append(
                    RetiredStrategyRule(
                        kind=field,
                        rule=rule.model_dump(mode="json", by_alias=True),
                        reason=str(error),
                    )
                )
            else:
                rules.append(rule)
    return StrategySettings(**kept), retired
