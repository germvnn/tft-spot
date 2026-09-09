"""Augment equivalence for matching; raw records and curated IDs stay intact."""

from typing import Any

from tft_spot.models.configuration import PriorityDecision


def build_augment_aliases(catalog: dict[str, dict[str, Any]]) -> dict[str, str]:
    representatives: dict[tuple[int, int, str], str] = {}
    aliases: dict[str, str] = {}
    for api_name, entity in catalog.items():
        try:
            key = (entity["set"], entity["tier"], entity["name"])
        except KeyError as error:
            raise ValueError(
                f"Missing augment identity field for {api_name}: {error}"
            ) from error
        if key[1] not in (1, 2, 3) or not isinstance(key[2], str) or not key[2]:
            raise ValueError(f"Invalid augment identity for {api_name}")
        aliases[api_name] = representatives.setdefault(key, api_name)
    return aliases


def resolve_augment_decisions(
    decisions: list[PriorityDecision], aliases: dict[str, str], source_id: str
) -> list[PriorityDecision]:
    """Use the same equivalence validation at save and compile time."""
    grouped: dict[str, PriorityDecision] = {}
    for decision in decisions:
        if decision.api_name not in aliases:
            raise ValueError(f"Unknown augment apiName: {decision.api_name}")
        representative = aliases[decision.api_name]
        previous = grouped.get(representative)
        if previous and previous.priority != decision.priority:
            raise ValueError(
                f"Conflicting priorities for equivalent augment {representative} "
                f"in composition {source_id}: {previous.priority}, {decision.priority}"
            )
        grouped.setdefault(
            representative, decision.model_copy(update={"api_name": representative})
        )
    return list(grouped.values())
