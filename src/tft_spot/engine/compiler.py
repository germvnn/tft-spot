"""Explicit adapter from the configurator workspace into validated engine input."""

from typing import Any

from tft_spot.data.augment_identity import resolve_augment_decisions
from tft_spot.models.composition import EngineComposition
from tft_spot.models.configuration import CompositionConfiguration
from tft_spot.models.strategy import validate_strategy


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
        payload["augments"] = [
            decision.model_dump()
            for decision in resolve_augment_decisions(
                config.augments, augment_aliases, config.source_id
            )
        ]
    if catalogs is not None:
        validate_strategy(config, catalogs)
        from tft_spot.engine.item_fit import compile_item_context

        payload["itemContext"] = compile_item_context(workspace, catalogs)
    if augment_aliases is not None:
        for rule in payload["strategy"]["augmentConditions"]:
            rule["augmentApiName"] = augment_aliases[rule["augmentApiName"]]
    return EngineComposition.model_validate(payload)
