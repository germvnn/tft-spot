from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import tft_spot.configurator.repository as repository_module
from tft_spot.configurator.repository import ConfigurationRepository
from tft_spot.models.configuration import (
    CompositionConfiguration,
    PriorityDecision,
    ScoringWeights,
)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def build_source_fixture(root: Path) -> dict[str, Any]:
    raw = root / "data" / "raw" / "tft_academy"
    write_json(
        raw / "compositions" / "index.json",
        {
            "compositions": [
                {
                    "backend_id": "source-1",
                    "visible_name": "Example comp",
                    "slug": "set-18-example",
                    "response_file": (
                        "data/raw/tft_academy/compositions/source-1.json"
                    ),
                }
            ]
        },
    )
    write_json(raw / "compositions" / "source-1.json", {})
    write_json(
        raw / "champions.json",
        {
            "champions": [
                {
                    "apiName": "DA_Champion",
                    "name": "Champion",
                    "championSquareIcon": "champion.png",
                },
                {
                    "apiName": "DA_Early",
                    "name": "Early unit",
                    "championSquareIcon": "early.png",
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
                    "icon": "item.png",
                    "type": "craftables",
                    "composition": ["DA_Component_A", "DA_Component_B"],
                },
                {
                    "apiName": "DA_Component_A",
                    "name": "Component A",
                    "icon": "a.png",
                    "type": "components",
                    "composition": [],
                },
                {
                    "apiName": "DA_Component_B",
                    "name": "Component B",
                    "icon": "b.png",
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
                    "icon": "augment.png",
                }
            ]
        },
    )
    return {
        "id": "source-1",
        "title": "Example comp",
        "compSlug": "set-18-example",
        "set": 18,
        "tier": "A",
        "style": "Fast 8",
        "difficulty": "MEDIUM",
        "mainChampion": {"apiName": "DA_Champion"},
        "carousel": [
            {"apiName": "DA_Item"},
            {"apiName": "DA_Component_A"},
        ],
        "earlyComp": [
            {
                "apiName": "DA_Early",
                "stars": 1,
                "items": ["DA_Item"],
            }
        ],
        "finalComp": [
            {
                "apiName": "DA_Champion",
                "boardIndex": 3,
                "stars": 2,
                "items": ["DA_Item"],
            }
        ],
        "augments": [{"apiName": "DA_Augment", "disabled": False}],
    }


def test_scoring_weights_must_add_up_to_one_hundred() -> None:
    assert ScoringWeights().units == 40

    with pytest.raises(ValidationError, match="add up to 100"):
        ScoringWeights(units=50, components=30, augments=30)


def test_ready_configuration_rejects_unset_decisions() -> None:
    with pytest.raises(ValidationError, match="cannot contain unset"):
        CompositionConfiguration(
            sourceId="source-1",
            setNumber=18,
            status="ready",
            components=[{"apiName": "DA_Component_A", "priority": "unset"}],
            augments=[],
        )


def test_repository_resolves_raw_entities_and_saves_curated_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(
        repository_module,
        "extract_queried_guide",
        lambda _payload: guide,
    )
    repository = ConfigurationRepository(tmp_path)

    workspace = repository.get_workspace("source-1")

    assert [unit["name"] for unit in workspace["finalUnits"]] == ["Champion"]
    assert [unit["name"] for unit in workspace["earlyUnits"]] == ["Early unit"]
    assert workspace["itemRecommendations"][0]["name"] == "Finished item"
    assert [
        component["name"]
        for component in workspace["itemRecommendations"][0]["components"]
    ] == ["Component A", "Component B"]
    assert [
        (component["apiName"], component["requiredCount"])
        for component in workspace["components"]
    ] == [("DA_Component_A", 2), ("DA_Component_B", 1)]
    assert workspace["configuration"]["status"] == "draft"
    assert "units" not in workspace["configuration"]
    assert {
        decision["priority"] for decision in workspace["configuration"]["components"]
    } == {"high"}
    assert {
        decision["priority"] for decision in workspace["configuration"]["augments"]
    } == {"medium"}

    saved = repository.save_configuration(
        "source-1",
        CompositionConfiguration(
            sourceId="source-1",
            setNumber=18,
            status="ready",
            components=[
                PriorityDecision(apiName="DA_Component_A", priority="high"),
                PriorityDecision(apiName="DA_Component_B", priority="medium"),
            ],
            augments=[
                PriorityDecision(
                    apiName="DA_Augment",
                    priority="high",
                )
            ],
        ),
    )

    output = tmp_path / "data" / "curated" / "set-18" / "compositions" / "source-1.json"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert saved.updated_at is not None
    assert payload["sourceId"] == "source-1"
    assert payload["status"] == "ready"
    assert payload["augments"][0] == {
        "apiName": "DA_Augment",
        "priority": "high",
    }
