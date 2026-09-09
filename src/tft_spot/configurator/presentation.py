"""Explicit presentation of source records; no scoring or persistence."""

from typing import Any
from urllib.parse import quote

from tft_spot.data.snapshot import ConfiguratorDataError


def entity_card(
    entity: dict[str, Any],
    category: str,
    image_fields: tuple[str, ...],
) -> dict[str, Any]:
    filename = next(
        (str(entity[field]) for field in image_fields if entity.get(field)),
        None,
    )
    return {
        "apiName": str(entity["apiName"]),
        "name": str(entity.get("name") or entity["apiName"]),
        "imageUrl": (
            f"/game-assets/{category}/{quote(filename)}" if filename else None
        ),
        "type": entity.get("type"),
        **({"role": entity["role"]} if "role" in entity else {}),
    }


def require_entity(
    catalog: dict[str, dict[str, Any]],
    api_name: str,
    entity_type: str,
) -> dict[str, Any]:
    try:
        return catalog[api_name]
    except KeyError as error:
        raise ConfiguratorDataError(
            f"Unknown {entity_type} apiName: {api_name}"
        ) from error


def unit_cards(
    raw_units: list[dict[str, Any]],
    *,
    champions: dict[str, dict[str, Any]],
    items: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            **entity_card(
                require_entity(champions, unit["apiName"], "champion"),
                "champions",
                ("championSquareIcon", "championIcon"),
            ),
            "boardIndex": unit.get("boardIndex"),
            "stars": unit.get("stars"),
            "items": [
                entity_card(
                    require_entity(items, item_api_name, "item"),
                    "items",
                    ("icon",),
                )
                for item_api_name in unit.get("items", [])
            ],
        }
        for unit in raw_units
    ]


def build_workspace(
    guide: dict[str, Any], entry: dict[str, Any], catalogs: dict
) -> dict[str, Any]:
    source_id = str(entry["backend_id"])
    champions = catalogs["champions"]
    items = catalogs["items"]
    augments = catalogs["augments"]

    final_units = unit_cards(
        guide.get("finalComp", []),
        champions=champions,
        items=items,
    )
    early_units = unit_cards(
        guide.get("earlyComp", []),
        champions=champions,
        items=items,
    )

    item_recommendations: list[dict[str, Any]] = []
    component_counts: dict[str, int] = {}
    for recommendation in guide.get("carousel", []):
        item_api_name = str(recommendation["apiName"])
        item = require_entity(items, item_api_name, "item")
        recipe_api_names = [
            str(api_name) for api_name in (item.get("composition") or [])
        ]
        recipe = [
            entity_card(
                require_entity(items, api_name, "component"),
                "items",
                ("icon",),
            )
            for api_name in recipe_api_names
        ]
        item_recommendations.append(
            {
                **entity_card(item, "items", ("icon",)),
                "components": recipe,
            }
        )

        demanded_components = (
            [item_api_name] if item.get("type") == "components" else recipe_api_names
        )
        for component_api_name in demanded_components:
            require_entity(items, component_api_name, "component")
            component_counts[component_api_name] = (
                component_counts.get(component_api_name, 0) + 1
            )

    components = [
        {
            **entity_card(
                require_entity(items, api_name, "component"),
                "items",
                ("icon",),
            ),
            "requiredCount": required_count,
        }
        for api_name, required_count in component_counts.items()
    ]
    augment_cards = [
        {
            **entity_card(
                require_entity(augments, augment["apiName"], "augment"),
                "augments",
                ("icon",),
            ),
            "disabledAtSource": bool(augment.get("disabled", False)),
        }
        for augment in guide.get("augments", [])
    ]

    set_number = int(guide["set"])
    main_champion_api_name = (guide.get("mainChampion") or {}).get("apiName")
    main_champion = (
        entity_card(
            require_entity(champions, main_champion_api_name, "main champion"),
            "champions",
            ("championSquareIcon", "championIcon"),
        )
        if main_champion_api_name
        else None
    )

    return {
        "source": {
            "sourceId": source_id,
            "title": guide.get("title") or entry["visible_name"],
            "metaTitle": guide.get("metaTitle"),
            "slug": guide.get("compSlug"),
            "set": set_number,
            "tier": guide.get("tier"),
            "style": guide.get("style"),
            "difficulty": guide.get("difficulty"),
            "updatedAt": guide.get("updated"),
            "mainChampion": main_champion,
            "augmentTip": guide.get("augmentsTip"),
            "tips": guide.get("tips", []),
        },
        "strategyCatalog": {
            "champions": [
                entity_card(c, "champions", ("championSquareIcon",))
                for c in champions.values()
                if c.get("set") == set_number and c.get("cost") in (1, 2, 3)
            ],
            "targets": [
                entity_card(c, "champions", ("championSquareIcon",))
                for c in champions.values()
                if c.get("set") == set_number
            ],
            "items": [
                entity_card(i, "items", ("icon",))
                for i in items.values()
                if i.get("set") == set_number and i.get("type") == "craftables"
            ],
        },
        "finalUnits": final_units,
        "earlyUnits": early_units,
        "itemRecommendations": item_recommendations,
        "components": components,
        "augments": augment_cards,
    }
