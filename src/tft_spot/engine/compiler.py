"""Explicit adapter from the configurator workspace into validated engine input."""

from typing import Any

from tft_spot.models.composition import EngineComposition
from tft_spot.models.configuration import CompositionConfiguration, PriorityDecision


def compile_workspace(
    workspace: dict[str, Any], augment_aliases: dict[str, str] | None = None
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
    return EngineComposition.model_validate(payload)
