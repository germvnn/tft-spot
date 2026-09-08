"""Augment equivalence for matching; raw records and curated IDs stay intact."""

from typing import Any


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
