from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tft_spot.configurator.presentation import build_workspace
from tft_spot.data.augment_identity import (
    build_augment_aliases,
    resolve_augment_decisions,
)
from tft_spot.data.snapshot import ConfiguratorDataError, SourceSnapshot
from tft_spot.data.tft_academy import (
    TftAcademyDataError,
    extract_guides,
    extract_queried_guide,
)
from tft_spot.models.configuration import (
    CompositionConfiguration,
    PriorityDecision,
    ScoringWeights,
    StrategySettings,
    UnitPriorityDecision,
)
from tft_spot.models.strategy import reconcile_strategy, validate_strategy


class CompositionNotFoundError(ConfiguratorDataError):
    pass


class ConfigurationRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw_dir = root / "data" / "raw" / "tft_academy"
        self.assets_dir = root / "data" / "assets"

    def list_compositions(
        self, snapshot: SourceSnapshot | None = None
    ) -> list[dict[str, Any]]:
        index = (
            snapshot.index
            if snapshot
            else self._read_json(self.raw_dir / "compositions" / "index.json")
        )
        result: list[dict[str, Any]] = []
        for position, entry in enumerate(index["compositions"]):
            source_id = str(entry["backend_id"])
            result.append(
                {
                    "sourceId": source_id,
                    "title": str(entry["visible_name"]),
                    "slug": entry.get("slug"),
                    "position": position,
                    "configured": any(
                        (self.root / "data" / "curated").glob(
                            f"set-*/compositions/{source_id}.json"
                        )
                    ),
                }
            )
        return result

    def get_workspace(
        self,
        source_id: str,
        *,
        reconcile_configuration: bool = False,
        snapshot: SourceSnapshot | None = None,
    ) -> dict[str, Any]:
        _index, entry = self._find_entry(source_id, snapshot)
        if snapshot is None:
            response_path = self.root / str(entry["response_file"])
            guide = self._extract_indexed_guide(
                self._read_json(response_path), source_id
            )
            catalogs = self.load_catalogs()
        else:
            guide = snapshot.guides[source_id]
            catalogs = snapshot.catalogs
        workspace = build_workspace(guide, entry, catalogs)
        configuration = self._load_or_default_configuration(
            source_id=source_id,
            set_number=workspace["source"]["set"],
            unit_api_names=list(
                dict.fromkeys(u["apiName"] for u in workspace["earlyUnits"])
            ),
            component_api_names=[c["apiName"] for c in workspace["components"]],
            augment_api_names=[a["apiName"] for a in workspace["augments"]],
            reconcile=reconcile_configuration,
        )
        if reconcile_configuration:
            strategy, retired = reconcile_strategy(configuration, catalogs)
            configuration = configuration.model_copy(
                update={
                    "strategy": strategy,
                    "retired_strategy_rules": [
                        *configuration.retired_strategy_rules,
                        *retired,
                    ],
                    "status": "draft" if retired else configuration.status,
                }
            )
        workspace["configuration"] = configuration.model_dump(
            mode="json", by_alias=True
        )
        return workspace

    def save_configuration(
        self,
        source_id: str,
        configuration: CompositionConfiguration,
        *,
        reconcile_existing: bool = False,
        snapshot: SourceSnapshot | None = None,
    ) -> CompositionConfiguration:
        workspace = self.get_workspace(
            source_id,
            reconcile_configuration=reconcile_existing,
            snapshot=snapshot,
        )
        try:
            catalogs = snapshot.catalogs if snapshot else self.load_catalogs()
            validate_strategy(configuration, catalogs)
            resolve_augment_decisions(
                configuration.augments,
                build_augment_aliases(catalogs["augments"]),
                configuration.source_id,
            )
        except ValueError as error:
            raise ConfiguratorDataError(str(error)) from error
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
        snapshot = self.load_snapshot()
        prepared: list[tuple[str, CompositionConfiguration]] = []
        for composition in self.list_compositions(snapshot):
            source_id = str(composition["sourceId"])
            workspace = self.get_workspace(source_id, snapshot=snapshot)
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
                        strategy=current.strategy,
                        retired_strategy_rules=current.retired_strategy_rules,
                        notes=current.notes,
                        updated_at=current.updated_at,
                    ),
                )
            )

        return [
            self.save_configuration(source_id, configuration, snapshot=snapshot)
            for source_id, configuration in prepared
        ]

    def reconcile_configurations(
        self,
        *,
        ready_source_ids: set[str],
        snapshot: SourceSnapshot | None = None,
    ) -> list[CompositionConfiguration]:
        """Align curated decisions with refreshed raw guides.

        Existing decisions for apiNames still present in the guide are preserved.
        Obsolete decisions are dropped, newly discovered ones receive the normal
        defaults, and only new or materially changed files are written.
        """
        snapshot = snapshot or self.load_snapshot()
        saved: list[CompositionConfiguration] = []
        for composition in self.list_compositions(snapshot):
            source_id = str(composition["sourceId"])
            workspace = self.get_workspace(
                source_id,
                reconcile_configuration=True,
                snapshot=snapshot,
            )
            current = CompositionConfiguration.model_validate(
                workspace["configuration"]
            )
            desired = current.model_copy(
                update={"status": "ready"} if source_id in ready_source_ids else {}
            )
            target = self._configuration_path(desired.set_number, source_id)
            if target.exists():
                existing = CompositionConfiguration.model_validate(
                    self._read_json(target)
                )
                if self._configuration_content(existing) == self._configuration_content(
                    desired
                ):
                    continue
            saved.append(
                self.save_configuration(
                    source_id,
                    desired,
                    reconcile_existing=True,
                    snapshot=snapshot,
                )
            )
        return saved

    def delete_configurations(
        self,
        *,
        set_number: int,
        source_ids: set[str],
    ) -> list[str]:
        deleted: list[str] = []
        for source_id in sorted(source_ids):
            target = self._configuration_path(set_number, source_id)
            if target.exists():
                target.unlink()
                deleted.append(source_id)
        return deleted

    def snapshot_set_number(self) -> int:
        index = self._read_json(self.raw_dir / "compositions" / "index.json")
        indexed_set = index.get("set")
        try:
            if indexed_set is not None and int(indexed_set) > 0:
                return int(indexed_set)
        except TypeError, ValueError:
            pass

        guide_sets: set[int] = set()
        for entry in index.get("compositions", []):
            try:
                response_path = self.root / str(entry["response_file"])
                guide = self._extract_indexed_guide(
                    self._read_json(response_path),
                    str(entry["backend_id"]),
                )
                set_number = int(guide["set"])
            except (KeyError, TypeError, ValueError) as error:
                raise ConfiguratorDataError(
                    "Could not determine set number from a raw composition guide"
                ) from error
            if set_number <= 0:
                raise ConfiguratorDataError(
                    "Raw composition guide contains an invalid set number"
                )
            guide_sets.add(set_number)

        if len(guide_sets) == 1:
            return guide_sets.pop()
        raise ConfiguratorDataError(
            "Composition index has no valid set number and raw guides "
            f"contain {len(guide_sets)} distinct set numbers"
        )

    @staticmethod
    def _extract_indexed_guide(
        payload: dict[str, Any],
        source_id: str,
    ) -> dict[str, Any]:
        try:
            guides = extract_guides(payload)
        except TftAcademyDataError:
            guides = []
        for guide in guides:
            if str(guide.get("id")) == source_id:
                return guide

        try:
            guide = extract_queried_guide(payload)
        except TftAcademyDataError as error:
            raise ConfiguratorDataError(
                f"Raw guide payload does not contain sourceId: {source_id}"
            ) from error
        if str(guide.get("id")) != source_id:
            raise ConfiguratorDataError(
                f"Raw guide payload does not contain sourceId: {source_id}"
            )
        return guide

    def _find_entry(
        self, source_id: str, snapshot: SourceSnapshot | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        index = (
            snapshot.index
            if snapshot
            else self._read_json(self.raw_dir / "compositions" / "index.json")
        )
        for entry in index["compositions"]:
            if str(entry["backend_id"]) == source_id:
                return index, entry
        raise CompositionNotFoundError(f"Unknown TFT Academy composition: {source_id}")

    def load_snapshot(self) -> SourceSnapshot:
        """Read each raw JSON once and decode each guide collection once per operation."""
        index = self._read_json(self.raw_dir / "compositions" / "index.json")
        catalogs = self.load_catalogs()
        collections: dict[Path, dict[str, Any]] = {}
        selected: dict[str, dict[str, Any]] = {}
        for entry in index["compositions"]:
            path = self.root / entry["response_file"]
            source_id = str(entry["backend_id"])
            if path not in collections:
                payload = self._read_json(path)
                try:
                    guides = extract_guides(payload)
                except TftAcademyDataError:
                    guides = [extract_queried_guide(payload)]
                collections[path] = {str(guide["id"]): guide for guide in guides}
            if source_id not in collections[path]:
                raise ConfiguratorDataError(
                    f"Raw guide payload does not contain sourceId: {source_id}"
                )
            selected[source_id] = collections[path][source_id]
        return SourceSnapshot(index=index, catalogs=catalogs, guides=selected)

    def load_catalogs(self) -> dict[str, dict[str, dict[str, Any]]]:
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
        reconcile: bool = False,
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
            if not reconcile:
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
            strategy=existing.strategy if existing else StrategySettings(),
            retired_strategy_rules=existing.retired_strategy_rules if existing else [],
            notes=existing.notes if existing else "",
            updated_at=existing.updated_at if existing else None,
        )

    def _configuration_path(self, set_number: int, source_id: str) -> Path:
        if not source_id or Path(source_id).name != source_id:
            raise ConfiguratorDataError(f"Unsafe composition sourceId: {source_id!r}")
        return (
            self.root
            / "data"
            / "curated"
            / f"set-{set_number}"
            / "compositions"
            / f"{source_id}.json"
        )

    @staticmethod
    def _configuration_content(
        configuration: CompositionConfiguration,
    ) -> dict[str, Any]:
        payload = configuration.model_dump(mode="json", by_alias=True)
        payload.pop("updatedAt", None)
        return payload

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
