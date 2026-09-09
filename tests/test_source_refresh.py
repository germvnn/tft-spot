from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import tft_spot.configurator.repository as repository_module
from tft_spot.configurator.repository import ConfigurationRepository
from tft_spot.configurator.source_refresh import (
    SourceRefreshError,
    refresh_tft_academy,
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def guide(source_id: str, component_mode: str) -> dict[str, Any]:
    carousel = (
        [{"apiName": "DA_Component_A"}]
        if component_mode == "single"
        else [{"apiName": "DA_Item"}]
    )
    return {
        "id": source_id,
        "title": f"Composition {source_id}",
        "compSlug": f"set-18-{source_id}",
        "set": 18,
        "tier": "A",
        "style": "Fast 8",
        "difficulty": "MEDIUM",
        "mainChampion": {"apiName": "DA_Champion"},
        "carousel": carousel,
        "earlyComp": [
            {
                "apiName": "DA_Early",
                "stars": 1,
                "items": [],
            }
        ],
        "finalComp": [
            {
                "apiName": "DA_Champion",
                "stars": 2,
                "items": ["DA_Item"],
            }
        ],
        "augments": [{"apiName": "DA_Augment", "disabled": False}],
    }


def write_snapshot(
    data_dir: Path,
    compositions: list[tuple[str, str]],
    *,
    asset_marker: str,
) -> None:
    raw = data_dir / "raw" / "tft_academy"
    entries = []
    for source_id, component_mode in compositions:
        response = raw / "compositions" / f"{source_id}.json"
        write_json(response, {"guide": guide(source_id, component_mode)})
        entries.append(
            {
                "backend_id": source_id,
                "visible_name": f"Composition {source_id}",
                "slug": f"set-18-{source_id}",
                "response_file": (
                    f"data/raw/tft_academy/compositions/{source_id}.json"
                ),
            }
        )
    write_json(
        raw / "compositions" / "index.json",
        {"set": 18, "compositions": entries},
    )
    write_json(
        raw / "champions.json",
        {
            "champions": [
                {
                    "apiName": "DA_Champion",
                    "name": "Champion",
                    "id": "champion-source",
                    "set": 18,
                    "cost": 4,
                },
                {
                    "apiName": "DA_Early",
                    "name": "Early unit",
                    "id": "early-source",
                    "set": 18,
                    "cost": 1,
                },
            ]
        },
    )
    write_json(
        raw / "items.json",
        {
            "items": [
                {
                    "apiName": "DA_Item",
                    "name": "Finished item",
                    "id": "item-source",
                    "set": 18,
                    "type": "craftables",
                    "composition": ["DA_Component_A", "DA_Component_B"],
                },
                {
                    "apiName": "DA_Component_A",
                    "name": "Component A",
                    "id": "component-a-source",
                    "set": 18,
                    "type": "components",
                    "composition": [],
                },
                {
                    "apiName": "DA_Component_B",
                    "name": "Component B",
                    "id": "component-b-source",
                    "set": 18,
                    "type": "components",
                    "composition": [],
                },
            ]
        },
    )
    write_json(
        raw / "augments.json",
        {
            "augments": [
                {
                    "apiName": "DA_Augment",
                    "name": "Augment",
                    "tier": 2,
                    "set": 18,
                    "id": "augment-source",
                }
            ]
        },
    )
    write_json(raw / "traits.json", {"traits": []})
    write_json(raw / "manifest.json", {"set": 18})
    assets = data_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "marker.txt").write_text(asset_marker, encoding="utf-8")


def test_refresh_adds_and_removes_compositions_and_reconciles_curated_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "extract_queried_guide",
        lambda payload: payload["guide"],
    )
    write_snapshot(
        tmp_path / "data",
        [("keep", "recipe"), ("removed", "recipe")],
        asset_marker="old",
    )
    repository = ConfigurationRepository(tmp_path)
    configurations = repository.bootstrap_ready_configurations()
    keep = next(
        configuration
        for configuration in configurations
        if configuration.source_id == "keep"
    )
    keep.components[0].priority = "low"
    keep.notes = "manual decision"
    repository.save_configuration("keep", keep)

    def runner(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        data_dir = Path(command[command.index("--data-dir") + 1])
        write_snapshot(
            data_dir,
            [("keep", "single"), ("new", "recipe")],
            asset_marker="fresh",
        )
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    result = refresh_tft_academy(tmp_path, repository, runner=runner)

    assert result.added_source_ids == ("new",)
    assert result.removed_source_ids == ("removed",)
    assert result.removed_configuration_source_ids == ("removed",)
    assert result.reconciled_source_ids == ("keep", "new")
    assert [
        composition["sourceId"] for composition in repository.list_compositions()
    ] == ["keep", "new"]
    assert (tmp_path / "data" / "assets" / "marker.txt").read_text(
        encoding="utf-8"
    ) == "fresh"
    assert not (
        tmp_path / "data" / "raw" / "tft_academy" / "compositions" / "removed.json"
    ).exists()
    assert not (
        tmp_path / "data" / "curated" / "set-18" / "compositions" / "removed.json"
    ).exists()

    keep_configuration = repository.get_workspace("keep")["configuration"]
    assert keep_configuration["status"] == "ready"
    assert keep_configuration["notes"] == "manual decision"
    assert keep_configuration["components"] == [
        {"apiName": "DA_Component_A", "priority": "low"}
    ]
    new_configuration = repository.get_workspace("new")["configuration"]
    assert new_configuration["status"] == "ready"


def test_refresh_failure_keeps_the_live_snapshot_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        repository_module,
        "extract_queried_guide",
        lambda payload: payload["guide"],
    )
    write_snapshot(
        tmp_path / "data",
        [("keep", "recipe")],
        asset_marker="old",
    )
    repository = ConfigurationRepository(tmp_path)
    index = repository.raw_dir / "compositions" / "index.json"
    before = index.read_bytes()

    def runner(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="",
            stderr="upstream offline",
        )

    with pytest.raises(SourceRefreshError, match="upstream offline"):
        refresh_tft_academy(tmp_path, repository, runner=runner)

    assert index.read_bytes() == before
    assert (tmp_path / "data" / "assets" / "marker.txt").read_text(
        encoding="utf-8"
    ) == "old"
    assert list(tmp_path.glob(".tft-spot-refresh-*")) == []
