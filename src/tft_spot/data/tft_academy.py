from __future__ import annotations

import math
from typing import Any


class TftAcademyDataError(ValueError):
    pass


def unflatten_sveltekit_data(values: list[Any]) -> Any:
    if not values:
        raise TftAcademyDataError("SvelteKit data array is empty")

    memo: dict[int, Any] = {}
    special = {
        -1: None,
        -2: None,
        -3: math.nan,
        -4: math.inf,
        -5: -math.inf,
        -6: -0.0,
    }

    def reference(value: Any) -> Any:
        if isinstance(value, bool) or not isinstance(value, int):
            return value
        if value < 0:
            return special.get(value)
        return hydrate(value)

    def hydrate(index: int) -> Any:
        if index in memo:
            return memo[index]
        if index >= len(values):
            raise TftAcademyDataError(
                f"SvelteKit reference {index} exceeds data size {len(values)}"
            )

        value = values[index]
        if isinstance(value, dict):
            result: Any = {}
            memo[index] = result
            result.update({key: reference(item) for key, item in value.items()})
            return result

        if isinstance(value, list):
            if value and isinstance(value[0], str):
                tag = value[0]
                if tag == "Date":
                    result = value[1]
                elif tag == "BigInt":
                    result = int(value[1])
                elif tag == "Set":
                    result = [reference(item) for item in value[1:]]
                elif tag == "Map":
                    result = {
                        reference(value[position]): reference(value[position + 1])
                        for position in range(1, len(value), 2)
                    }
                else:
                    raise TftAcademyDataError(f"Unsupported SvelteKit tag: {tag!r}")
                memo[index] = result
                return result

            result = []
            memo[index] = result
            result.extend(reference(item) for item in value)
            return result

        memo[index] = value
        return value

    return hydrate(0)


def extract_queried_guide(payload: dict[str, Any]) -> dict[str, Any]:
    for node in payload.get("nodes", []):
        if not isinstance(node, dict) or not isinstance(node.get("data"), list):
            continue
        decoded = unflatten_sveltekit_data(node["data"])
        if isinstance(decoded, dict):
            guide = decoded.get("queriedGuide")
            if isinstance(guide, dict):
                return guide
    raise TftAcademyDataError("Could not find queriedGuide in SvelteKit response")
