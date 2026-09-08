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
    UnitPriorityDecision,
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
                    "id": "champion-source",
                    "set": 18,
                    "cost": 4,
                    "championSquareIcon": "champion.png",
                },
                {
                    "apiName": "DA_Early",
                    "name": "Early unit",
                    "id": "early-source",
                    "set": 18,
                    "cost": 1,
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
                    "id": "item-source",
                    "set": 18,
                    "icon": "item.png",
                    "type": "craftables",
                    "composition": ["DA_Component_A", "DA_Component_B"],
                },
                {
                    "apiName": "DA_Component_A",
                    "name": "Component A",
                    "id": "component-a-source",
                    "set": 18,
                    "icon": "a.png",
                    "type": "components",
                    "composition": [],
                },
                {
                    "apiName": "DA_Component_B",
                    "name": "Component B",
                    "id": "component-b-source",
                    "set": 18,
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
                    "tier": 2,
                    "set": 18,
                    "id": "augment-source",
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
    assert workspace["configuration"]["units"] == [
        {"apiName": "DA_Early", "priority": "medium", "core": False}
    ]
    assert {
        decision["priority"] for decision in workspace["configuration"]["components"]
    } == {"essential"}
    assert {
        decision["priority"] for decision in workspace["configuration"]["augments"]
    } == {"medium"}

    saved = repository.save_configuration(
        "source-1",
        CompositionConfiguration(
            sourceId="source-1",
            setNumber=18,
            status="ready",
            units=[UnitPriorityDecision(apiName="DA_Early", priority="high")],
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


def test_bootstrap_marks_every_configuration_ready_and_preserves_decisions(
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
    repository.save_configuration(
        "source-1",
        CompositionConfiguration(
            sourceId="source-1",
            setNumber=18,
            status="draft",
            components=[
                PriorityDecision(apiName="DA_Component_A", priority="low"),
                PriorityDecision(apiName="DA_Component_B", priority="unset"),
            ],
            augments=[
                PriorityDecision(apiName="DA_Augment", priority="unset"),
            ],
        ),
    )

    saved = repository.bootstrap_ready_configurations()

    assert [configuration.source_id for configuration in saved] == ["source-1"]
    assert saved[0].status == "ready"
    assert [
        (decision.api_name, decision.priority) for decision in saved[0].components
    ] == [
        ("DA_Component_A", "low"),
        ("DA_Component_B", "essential"),
    ]
    assert [
        (decision.api_name, decision.priority) for decision in saved[0].augments
    ] == [("DA_Augment", "medium")]


def test_engine_compiles_legacy_configuration_and_api_validates_inventory(
    tmp_path, monkeypatch
):
    from fastapi import HTTPException

    from tft_spot.configurator import api
    from tft_spot.engine.compiler import compile_workspace
    from tft_spot.models.spot import Spot

    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    repo = ConfigurationRepository(tmp_path)
    monkeypatch.setattr(api, "repository", repo)
    legacy = {
        "sourceId": "source-1",
        "setNumber": 18,
        "status": "ready",
        "components": [
            {"apiName": "DA_Component_A", "priority": "high"},
            {"apiName": "DA_Component_B", "priority": "medium"},
        ],
        "augments": [{"apiName": "DA_Augment", "priority": "high"}],
    }
    path = tmp_path / "data/curated/set-18/compositions/source-1.json"
    write_json(path, legacy)
    before = path.read_bytes()
    compiled = compile_workspace(repo.get_workspace("source-1"))
    assert compiled.units[0].priority == "medium"
    assert compiled.components[0].required_count == 2
    state = Spot(
        setNumber=18,
        offeredAugments=["DA_Augment"],
        units=[{"apiName": "DA_Early", "stars": 2}],
        components=[{"apiName": "DA_Component_A", "count": 2}],
    )
    result = api.recommendations(state)
    assert result["recommendations"][0]["eligible"] is True
    assert path.read_bytes() == before
    repo.save_configuration(
        "source-1",
        CompositionConfiguration.model_validate(
            repo.get_workspace("source-1")["configuration"]
        ),
    )
    assert json.loads(path.read_text())["units"][0]["priority"] == "medium"
    for change in (
        {"components": [{"apiName": "DA_Item"}]},
        {"units": [{"apiName": "unknown"}]},
        {"offeredAugments": ["unknown"]},
        {"setNumber": 99},
    ):
        with pytest.raises(HTTPException) as error:
            api.recommendations(Spot.model_validate({**state.model_dump(), **change}))
        assert error.value.status_code == 422


def test_ready_save_rejects_incomplete_units_and_bootstrap_preserves_priorities(
    tmp_path, monkeypatch
):
    from tft_spot.configurator.repository import ConfiguratorDataError

    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    repo = ConfigurationRepository(tmp_path)
    config = CompositionConfiguration.model_validate(
        repo.get_workspace("source-1")["configuration"]
    )
    config.status = "ready"
    config.units = []
    with pytest.raises(ConfiguratorDataError, match="all units"):
        repo.save_configuration("source-1", config)
    config.units = [UnitPriorityDecision(apiName="DA_Early", priority="essential")]
    repo.save_configuration("source-1", config)
    assert repo.bootstrap_ready_configurations()[0].units[0].priority == "essential"


def test_recommendations_http_contract(tmp_path, monkeypatch):
    import asyncio

    from tft_spot.configurator import api

    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    repo = ConfigurationRepository(tmp_path)
    monkeypatch.setattr(api, "repository", repo)

    async def request(payload):
        sent = []

        async def receive():
            return {
                "type": "http.request",
                "body": json.dumps(payload).encode(),
                "more_body": False,
            }

        async def send(message):
            sent.append(message)

        await api.app(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "path": "/api/recommendations",
                "raw_path": b"/api/recommendations",
                "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "scheme": "http",
                "server": ("test", 80),
                "client": ("test", 1),
                "root_path": "",
            },
            receive,
            send,
        )
        return sent[0]["status"], json.loads(
            b"".join(message.get("body", b"") for message in sent)
        )

    payload = {"setNumber": 18, "offeredAugments": ["DA_Augment"]}
    status, result = asyncio.run(request(payload))
    assert status == 200
    assert result["recommendations"] == []
    assert result["skipped"] == [
        {"sourceId": "source-1", "reason": "configuration_not_ready"}
    ]
    repo.bootstrap_ready_configurations()
    status, result = asyncio.run(request(payload))
    assert status == 200
    assert result["recommendations"][0]["bestAugmentApiName"] == "DA_Augment"
    assert result["recommendations"][0]["score"] == 15
    status, _ = asyncio.run(request({**payload, "items": ["DA_Item"]}))
    assert status == 422
    status, _ = asyncio.run(
        request({**payload, "units": [{"apiName": "DA_Early", "stars": 0}]})
    )
    assert status == 422


def test_spot_catalog_preserves_entities_and_exposes_rarity(tmp_path, monkeypatch):
    from tft_spot.configurator import api

    build_source_fixture(tmp_path)
    raw = tmp_path / "data/raw/tft_academy"
    for filename, key in (
        ("champions.json", "champions"),
        ("items.json", "items"),
        ("augments.json", "augments"),
    ):
        payload = json.loads((raw / filename).read_text())
        for index, entity in enumerate(payload[key]):
            entity.update({"id": f"source-{index}", "set": 18})
            if key == "champions":
                entity["cost"] = 0 if index == 0 else 4
            if key == "augments":
                entity.update(
                    {
                        "tier": 3,
                        "description": "Example",
                        "stages": ["2-1"],
                        "disabled": False,
                    }
                )
        write_json(raw / filename, payload)
    monkeypatch.setattr(api, "repository", ConfigurationRepository(tmp_path))
    result = api.spot_catalog()
    assert result["setNumbers"] == [18]
    assert [unit["cost"] for unit in result["champions"]] == [0, 4]
    assert len(result["components"]) == 2
    assert result["augments"][0]["tier"] == 3
    assert result["augments"][0]["stages"] == ["2-1"]
    assert result["champions"][0]["sourceId"] == "source-0"


def test_equivalent_augment_offers_match_core_alias_and_catalog_is_deduplicated(
    tmp_path, monkeypatch
):
    from fastapi import HTTPException

    from tft_spot.configurator import api
    from tft_spot.models.spot import Spot

    guide = build_source_fixture(tmp_path)
    guide["augments"] = [{"apiName": "flora-later"}]
    raw = tmp_path / "data/raw/tft_academy/augments.json"
    write_json(
        raw,
        {
            "augments": [
                {
                    "apiName": name,
                    "id": name + "-source",
                    "set": 18,
                    "name": "Consuming Flora",
                    "tier": 2,
                    "stages": [stage],
                }
                for name, stage in (
                    ("flora", "2-1"),
                    ("flora-later", "3-2"),
                    ("flora-last", "4-2"),
                )
            ]
            + [
                {
                    "apiName": "flora-silver",
                    "id": "silver-source",
                    "set": 18,
                    "name": "Consuming Flora",
                    "tier": 1,
                }
            ]
        },
    )
    before = raw.read_bytes()
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    repo = ConfigurationRepository(tmp_path)
    monkeypatch.setattr(api, "repository", repo)
    config = repo.bootstrap_ready_configurations()[0]
    config.augments[0].priority = "essential"
    repo.save_configuration("source-1", config)
    curated = tmp_path / "data/curated/set-18/compositions/source-1.json"
    curated_before = curated.read_bytes()
    catalog = api.spot_catalog()
    assert len(catalog["augments"]) == 2
    assert catalog["augments"][0]["aliasApiNames"] == [
        "flora",
        "flora-later",
        "flora-last",
    ]
    assert [v["stages"] for v in catalog["augments"][0]["variants"]] == [
        ["2-1"],
        ["3-2"],
        ["4-2"],
    ]
    results = [
        api.recommendations(Spot(setNumber=18, offeredAugments=[name]))
        for name in ("flora", "flora-later", "flora-last")
    ]
    assert results[0] == results[1] == results[2]
    assert results[0]["recommendations"][0]["score"] == 30
    assert results[0]["recommendations"][0]["requiredAugmentApiName"] == "flora"
    assert (
        api.recommendations(Spot(setNumber=18, offeredAugments=["flora-silver"]))[
            "recommendations"
        ][0]["eligible"]
        is False
    )
    with pytest.raises(HTTPException) as error:
        api.recommendations(
            Spot(setNumber=18, offeredAugments=["flora", "flora-later"])
        )
    assert error.value.status_code == 422
    assert raw.read_bytes() == before
    assert curated.read_bytes() == curated_before


def test_core_defaults_false_and_survives_save_bootstrap_and_compilation(
    tmp_path, monkeypatch
):
    from tft_spot.engine.compiler import compile_workspace
    from tft_spot.engine.scoring import score_composition
    from tft_spot.models.spot import Spot

    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    repo = ConfigurationRepository(tmp_path)
    configs = repo.bootstrap_ready_configurations()
    assert configs[0].units[0].core is False
    before = compile_workspace(repo.get_workspace("source-1"))
    configs[0].units[0].core = True
    repo.save_configuration("source-1", configs[0])
    assert repo.bootstrap_ready_configurations()[0].units[0].core is True
    after = compile_workspace(repo.get_workspace("source-1"))
    assert after.units[0].core is True
    spot = Spot(
        setNumber=18,
        offeredAugments=["DA_Augment"],
        units=[{"apiName": "DA_Early", "count": 2}],
    )
    assert (
        score_composition(before, spot)["score"]
        > score_composition(after, spot)["score"]
    )
    assert score_composition(after, spot)["evidence"]["units"][0]["core"] is True
