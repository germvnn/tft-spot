from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from tft_spot.data.tft_academy import extract_queried_guide
from tft_spot.models.configuration import (
    CompositionConfiguration,
    PriorityDecision,
    ScoringWeights,
    UnitPriorityDecision,
)


class ConfiguratorDataError(ValueError):
    pass


class CompositionNotFoundError(ConfiguratorDataError):
    pass


class ConfigurationRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw_dir = root / "data" / "raw" / "tft_academy"
        self.assets_dir = root / "data" / "assets"

    def list_compositions(self) -> list[dict[str, Any]]:
        index = self._read_json(self.raw_dir / "compositions" / "index.json")
        result: list[dict[str, Any]] = []
        for position, entry in enumerate(index["compositions"]):
            source_id = str(entry["backend_id"])
            result.append(
                {
                    "sourceId": source_id,
                    "title": str(entry["visible_name"]),
                    "slug": str(entry["slug"]),
                    "position": position,
                    "configured": any(
                        (self.root / "data" / "curated").glob(
                            f"set-*/compositions/{source_id}.json"
                        )
                    ),
                }
            )
        return result

    def get_workspace(self, source_id: str) -> dict[str, Any]:
        _index, entry = self._find_entry(source_id)
        response_path = self.root / str(entry["response_file"])
        guide = extract_queried_guide(self._read_json(response_path))
        catalogs = self._load_catalogs()
        champions = catalogs["champions"]
        items = catalogs["items"]
        augments = catalogs["augments"]

        final_units = self._unit_cards(
            guide.get("finalComp", []),
            champions=champions,
            items=items,
        )
        early_units = self._unit_cards(
            guide.get("earlyComp", []),
            champions=champions,
            items=items,
        )

        item_recommendations: list[dict[str, Any]] = []
        component_counts: dict[str, int] = {}
        for recommendation in guide.get("carousel", []):
            item_api_name = str(recommendation["apiName"])
            item = self._require(items, item_api_name, "item")
            recipe_api_names = [
                str(api_name) for api_name in (item.get("composition") or [])
            ]
            recipe = [
                self._entity_card(
                    self._require(items, api_name, "component"),
                    "items",
                    ("icon",),
                )
                for api_name in recipe_api_names
            ]
            item_recommendations.append(
                {
                    **self._entity_card(item, "items", ("icon",)),
                    "components": recipe,
                }
            )

            demanded_components = (
                [item_api_name]
                if item.get("type") == "components"
                else recipe_api_names
            )
            for component_api_name in demanded_components:
                self._require(items, component_api_name, "component")
                component_counts[component_api_name] = (
                    component_counts.get(component_api_name, 0) + 1
                )

        components = [
            {
                **self._entity_card(
                    self._require(items, api_name, "component"),
                    "items",
                    ("icon",),
                ),
                "requiredCount": required_count,
            }
            for api_name, required_count in component_counts.items()
        ]
        augment_cards = [
            {
                **self._entity_card(
                    self._require(augments, augment["apiName"], "augment"),
                    "augments",
                    ("icon",),
                ),
                "disabledAtSource": bool(augment.get("disabled", False)),
            }
            for augment in guide.get("augments", [])
        ]

        set_number = int(guide["set"])
        configuration = self._load_or_default_configuration(
            source_id=source_id,
            set_number=set_number,
            unit_api_names=list(dict.fromkeys(unit["apiName"] for unit in early_units)),
            component_api_names=list(component_counts),
            augment_api_names=[augment["apiName"] for augment in augment_cards],
        )
        main_champion_api_name = (guide.get("mainChampion") or {}).get("apiName")
        main_champion = (
            self._entity_card(
                self._require(champions, main_champion_api_name, "main champion"),
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
                "slug": guide["compSlug"],
                "set": set_number,
                "tier": guide.get("tier"),
                "style": guide.get("style"),
                "difficulty": guide.get("difficulty"),
                "updatedAt": guide.get("updated"),
                "mainChampion": main_champion,
                "augmentTip": guide.get("augmentsTip"),
                "tips": guide.get("tips", []),
            },
            "finalUnits": final_units,
            "earlyUnits": early_units,
            "itemRecommendations": item_recommendations,
            "components": components,
            "augments": augment_cards,
            "configuration": configuration.model_dump(mode="json", by_alias=True),
        }

    def save_configuration(
        self, source_id: str, configuration: CompositionConfiguration
    ) -> CompositionConfiguration:
        workspace = self.get_workspace(source_id)
        source = workspace["source"]
        if configuration.source_id != source_id:
            raise ConfiguratorDataError("Configuration sourceId does not match route")
        if configuration.set_number != source["set"]:
            raise ConfiguratorDataError(
                "Configuration setNumber does not match raw guide"
            )

        self._validate_decisions(
            configuration.components,
            {component["apiName"] for component in workspace["components"]},
            "component",
        )
        self._validate_decisions(
            configuration.augments,
            {augment["apiName"] for augment in workspace["augments"]},
            "augment",
        )

        self._validate_decisions(
            configuration.units,
            {unit["apiName"] for unit in workspace["earlyUnits"]},
            "unit",
        )
        for field, cards in (
            ("units", "earlyUnits"),
            ("components", "components"),
            ("augments", "augments"),
        ):
            if configuration.status == "ready" and {
                d.api_name for d in getattr(configuration, field)
            } != {c["apiName"] for c in workspace[cards]}:
                raise ConfiguratorDataError(
                    f"Ready configuration requires all {field} decisions"
                )

        saved = configuration.model_copy(update={"updated_at": datetime.now(UTC)})
        target = self._configuration_path(saved.set_number, source_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                saved.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(target)
        return saved

    def bootstrap_ready_configurations(self) -> list[CompositionConfiguration]:
        prepared: list[tuple[str, CompositionConfiguration]] = []
        for composition in self.list_compositions():
            source_id = str(composition["sourceId"])
            workspace = self.get_workspace(source_id)
            current = CompositionConfiguration.model_validate(
                workspace["configuration"]
            )
            prepared.append(
                (
                    source_id,
                    CompositionConfiguration(
                        schema_version=current.schema_version,
                        source_id=current.source_id,
                        set_number=current.set_number,
                        status="ready",
                        weights=current.weights,
                        units=[
                            d.model_copy(
                                update={
                                    "priority": "medium"
                                    if d.priority == "unset"
                                    else d.priority
                                }
                            )
                            for d in current.units
                        ],
                        components=[
                            decision.model_copy(
                                update={
                                    "priority": (
                                        "essential"
                                        if decision.priority == "unset"
                                        else decision.priority
                                    )
                                }
                            )
                            for decision in current.components
                        ],
                        augments=[
                            decision.model_copy(
                                update={
                                    "priority": (
                                        "medium"
                                        if decision.priority == "unset"
                                        else decision.priority
                                    )
                                }
                            )
                            for decision in current.augments
                        ],
                        notes=current.notes,
                        updated_at=current.updated_at,
                    ),
                )
            )

        return [
            self.save_configuration(source_id, configuration)
            for source_id, configuration in prepared
        ]

    def _unit_cards(
        self,
        raw_units: list[dict[str, Any]],
        *,
        champions: dict[str, dict[str, Any]],
        items: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                **self._entity_card(
                    self._require(champions, unit["apiName"], "champion"),
                    "champions",
                    ("championSquareIcon", "championIcon"),
                ),
                "boardIndex": unit.get("boardIndex"),
                "stars": unit.get("stars"),
                "items": [
                    self._entity_card(
                        self._require(items, item_api_name, "item"),
                        "items",
                        ("icon",),
                    )
                    for item_api_name in unit.get("items", [])
                ],
            }
            for unit in raw_units
        ]

    def _find_entry(self, source_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        index = self._read_json(self.raw_dir / "compositions" / "index.json")
        for entry in index["compositions"]:
            if str(entry["backend_id"]) == source_id:
                return index, entry
        raise CompositionNotFoundError(f"Unknown TFT Academy composition: {source_id}")

    def _load_catalogs(self) -> dict[str, dict[str, dict[str, Any]]]:
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for root_key, filename in (
            ("champions", "champions.json"),
            ("items", "items.json"),
            ("augments", "augments.json"),
        ):
            payload = self._read_json(self.raw_dir / filename)
            result[root_key] = {
                str(entity["apiName"]): entity for entity in payload[root_key]
            }
        return result

    def _load_or_default_configuration(
        self,
        *,
        source_id: str,
        set_number: int,
        unit_api_names: list[str],
        component_api_names: list[str],
        augment_api_names: list[str],
    ) -> CompositionConfiguration:
        path = self._configuration_path(set_number, source_id)
        existing = (
            CompositionConfiguration.model_validate(self._read_json(path))
            if path.exists()
            else None
        )

        if existing:
            if existing.source_id != source_id or existing.set_number != set_number:
                raise ConfiguratorDataError(
                    "Stored configuration identity does not match raw guide"
                )
            for decisions, names, label in (
                (existing.units, unit_api_names, "unit"),
                (existing.components, component_api_names, "component"),
                (existing.augments, augment_api_names, "augment"),
            ):
                self._validate_decisions(decisions, set(names), label)
        unit_priorities = (
            {d.api_name: d.priority for d in existing.units} if existing else {}
        )
        unit_core = {d.api_name: d.core for d in existing.units} if existing else {}
        component_priorities = (
            {decision.api_name: decision.priority for decision in existing.components}
            if existing
            else {}
        )
        augment_priorities = (
            {decision.api_name: decision.priority for decision in existing.augments}
            if existing
            else {}
        )

        return CompositionConfiguration(
            source_id=source_id,
            set_number=set_number,
            status=existing.status if existing else "draft",
            weights=existing.weights if existing else ScoringWeights(),
            units=[
                UnitPriorityDecision(
                    api_name=name,
                    priority=unit_priorities.get(name, "medium"),
                    core=unit_core.get(name, False),
                )
                for name in unit_api_names
            ],
            components=[
                PriorityDecision(
                    api_name=api_name,
                    priority=component_priorities.get(api_name, "essential"),
                )
                for api_name in component_api_names
            ],
            augments=[
                PriorityDecision(
                    api_name=api_name,
                    priority=augment_priorities.get(api_name, "medium"),
                )
                for api_name in augment_api_names
            ],
            notes=existing.notes if existing else "",
            updated_at=existing.updated_at if existing else None,
        )

    def _configuration_path(self, set_number: int, source_id: str) -> Path:
        return (
            self.root
            / "data"
            / "curated"
            / f"set-{set_number}"
            / "compositions"
            / f"{source_id}.json"
        )

    @staticmethod
    def _entity_card(
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
        }

    @staticmethod
    def _require(
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

    @staticmethod
    def _validate_decisions(
        decisions: Sequence[PriorityDecision],
        candidates: set[str],
        label: str,
    ) -> None:
        api_names = [decision.api_name for decision in decisions]
        if len(api_names) != len(set(api_names)):
            raise ConfiguratorDataError(f"Duplicate {label} decisions are not allowed")
        unknown = set(api_names) - candidates
        if unknown:
            raise ConfiguratorDataError(f"Unknown {label} decisions: {sorted(unknown)}")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise ConfiguratorDataError(
                f"Required data file is missing: {path}"
            ) from error
