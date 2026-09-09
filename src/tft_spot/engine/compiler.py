"""Explicit adapter from the configurator workspace into validated engine input."""

from typing import Any

from tft_spot.models.composition import EngineComposition
from tft_spot.models.configuration import CompositionConfiguration, PriorityDecision


def compile_workspace(
    workspace: dict[str, Any],
    augment_aliases: dict[str, str] | None = None,
    catalogs: dict | None = None,
) -> EngineComposition:
    config = CompositionConfiguration.model_validate(workspace["configuration"])
    source = workspace["source"]
    if config.source_id != source["sourceId"] or config.set_number != source["set"]:
        raise ValueError("Configuration identity does not match workspace")
    for field, cards in (
        ("units", "earlyUnits"),
        ("components", "components"),
        ("augments", "augments"),
    ):
        if {d.api_name for d in getattr(config, field)} != {
            c["apiName"] for c in workspace[cards]
        }:
            raise ValueError(f"Incomplete or stale {field} decisions")
    counts = {c["apiName"]: c["requiredCount"] for c in workspace["components"]}
    payload = config.model_dump()
    payload["title"] = source["title"]
    payload["components"] = [
        dict(d.model_dump(), requiredCount=counts[d.api_name])
        for d in config.components
    ]
    if augment_aliases is not None:
        grouped: dict[str, PriorityDecision] = {}
        for decision in config.augments:
            if decision.api_name not in augment_aliases:
                raise ValueError(f"Unknown augment apiName: {decision.api_name}")
            representative = augment_aliases[decision.api_name]
            previous = grouped.get(representative)
            if previous and previous.priority != decision.priority:
                raise ValueError(
                    f"Conflicting priorities for equivalent augment {representative} "
                    f"in composition {config.source_id}: {previous.priority}, {decision.priority}"
                )
            grouped.setdefault(
                representative, decision.model_copy(update={"api_name": representative})
            )
        payload["augments"] = [decision.model_dump() for decision in grouped.values()]
    if catalogs is not None:
        validate_strategy(config, catalogs)
        from tft_spot.engine.item_fit import compile_item_context

        payload["itemContext"] = compile_item_context(workspace, catalogs)
    if augment_aliases is not None:
        for rule in payload["strategy"]["augmentConditions"]:
            rule["augmentApiName"] = augment_aliases[rule["augmentApiName"]]
    return EngineComposition.model_validate(payload)


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
