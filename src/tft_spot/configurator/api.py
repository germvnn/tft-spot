from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from tft_spot.configurator.repository import (
    CompositionNotFoundError,
    ConfigurationRepository,
    ConfiguratorDataError,
)
from tft_spot.data.augment_identity import build_augment_aliases
from tft_spot.engine.compiler import compile_workspace
from tft_spot.engine.scoring import SCORING_VERSION, rank_compositions
from tft_spot.engine.simulator import (
    Review,
    SimulationRequest,
    generate_run,
    list_runs,
    load_run,
    save_review,
)
from tft_spot.models.configuration import CompositionConfiguration
from tft_spot.models.spot import Spot

ROOT = Path(
    os.environ.get(
        "TFT_SPOT_ROOT",
        Path(__file__).resolve().parents[3],
    )
).resolve()
repository = ConfigurationRepository(ROOT)

app = FastAPI(
    title="TFT Spot Configurator API",
    version="0.1.0",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/compositions")
def list_compositions() -> dict[str, object]:
    try:
        compositions = repository.list_compositions()
    except ConfiguratorDataError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"compositions": compositions}


@app.post("/api/compositions/bootstrap-ready")
def bootstrap_ready_configurations() -> dict[str, object]:
    try:
        saved = repository.bootstrap_ready_configurations()
    except ConfiguratorDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "saved": len(saved),
        "sourceIds": [configuration.source_id for configuration in saved],
    }


@app.get("/api/compositions/{source_id}")
def get_composition(source_id: str) -> dict[str, object]:
    try:
        return repository.get_workspace(source_id)
    except CompositionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ConfiguratorDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.put("/api/compositions/{source_id}/configuration")
def save_configuration(
    source_id: str,
    configuration: CompositionConfiguration,
) -> dict[str, object]:
    try:
        saved = repository.save_configuration(source_id, configuration)
    except CompositionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ConfiguratorDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"configuration": saved.model_dump(mode="json", by_alias=True)}


if repository.assets_dir.exists():
    app.mount(
        "/game-assets",
        StaticFiles(directory=repository.assets_dir),
        name="assets",
    )


@app.post("/api/recommendations")
def recommendations(spot: Spot) -> dict[str, object]:
    try:
        catalogs = repository._load_catalogs()
        augment_aliases = build_augment_aliases(catalogs["augments"])
        for name in spot.offered_augments:
            entity = repository._require(catalogs["augments"], name, "augment")
            if entity["set"] != spot.set_number:
                raise ValueError(f"Augment belongs to a different set: {name}")
        spot = Spot.model_validate(
            {
                **spot.model_dump(),
                "offeredAugments": [
                    augment_aliases[name] for name in spot.offered_augments
                ],
            }
        )
        for unit in spot.units:
            repository._require(catalogs["champions"], unit.api_name, "champion")
        for component in spot.components:
            item = repository._require(
                catalogs["items"], component.api_name, "component"
            )
            if item.get("type") != "components":
                raise ValueError(f"Expected a loose component: {component.api_name}")
        compositions = []
        presentation = {}
        skipped = []
        for entry in repository.list_compositions():
            workspace = repository.get_workspace(entry["sourceId"])
            if workspace["source"]["set"] != spot.set_number:
                continue
            if workspace["configuration"]["status"] != "ready":
                skipped.append(
                    {"sourceId": entry["sourceId"], "reason": "configuration_not_ready"}
                )
                continue
            compositions.append(compile_workspace(workspace, augment_aliases, catalogs))
            presentation[entry["sourceId"]] = {
                "mainChampion": workspace["source"]["mainChampion"],
                "finalUnits": workspace["finalUnits"],
                "tier": workspace["source"]["tier"],
                "style": workspace["source"]["style"],
            }
        if not compositions and not skipped:
            raise ValueError(f"No compositions available for set {spot.set_number}")
        return {
            "scoringVersion": SCORING_VERSION,
            "recommendations": [
                {**result, **presentation[result["sourceId"]]}
                for result in rank_compositions(compositions, spot)
            ],
            "skipped": skipped,
        }
    except (ConfiguratorDataError, ValidationError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/spot-catalog")
def spot_catalog() -> dict[str, object]:
    """Preserve source order and entities; the player UI selects costs 1-3."""
    try:
        catalogs = repository._load_catalogs()
        champions = [
            {
                **repository._entity_card(
                    entity, "champions", ("championSquareIcon", "championIcon")
                ),
                "sourceId": entity["id"],
                "setNumber": entity["set"],
                "cost": entity["cost"],
            }
            for entity in catalogs["champions"].values()
        ]
        components = [
            {
                **repository._entity_card(entity, "items", ("icon",)),
                "sourceId": entity["id"],
                "setNumber": entity["set"],
            }
            for entity in catalogs["items"].values()
            if entity.get("type") == "components"
        ]
        augments = []
        aliases = build_augment_aliases(catalogs["augments"])
        members: dict[str, list[str]] = {}
        for api_name, representative in aliases.items():
            members.setdefault(representative, []).append(api_name)
        for representative, api_names in members.items():
            entity = catalogs["augments"][representative]
            if entity["tier"] not in (1, 2, 3):
                raise ValueError(f"Unknown augment tier: {entity['tier']}")
            augments.append(
                {
                    **repository._entity_card(entity, "augments", ("icon",)),
                    "sourceId": entity["id"],
                    "setNumber": entity["set"],
                    "tier": entity["tier"],
                    "description": entity.get("description"),
                    "stages": entity.get("stages"),
                    "disabledAtSource": entity.get("disabled"),
                    "aliasApiNames": api_names,
                    "variants": [
                        {
                            "apiName": name,
                            "sourceId": catalogs["augments"][name]["id"],
                            "stages": catalogs["augments"][name].get("stages"),
                            "description": catalogs["augments"][name].get(
                                "description"
                            ),
                            "disabledAtSource": catalogs["augments"][name].get(
                                "disabled"
                            ),
                        }
                        for name in api_names
                    ],
                }
            )
        return {
            "setNumbers": list(dict.fromkeys(c["setNumber"] for c in champions)),
            "champions": champions,
            "components": components,
            "augments": augments,
        }
    except (ConfiguratorDataError, ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


# Calibration runs and human reviews are local artifacts, separate from curated data.


@app.get("/api/simulator/runs")
def simulator_runs() -> dict:
    return {"runs": list_runs(ROOT)}


@app.post("/api/simulator/runs")
def simulator_generate(options: SimulationRequest) -> dict:
    try:
        return generate_run(ROOT, options)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/simulator/runs/{run_id}")
def simulator_load(run_id: str) -> dict:
    try:
        return load_run(ROOT, run_id)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404, detail="Unknown simulation run") from error


@app.put("/api/simulator/runs/{run_id}/reviews/{case_id}")
def simulator_review(run_id: str, case_id: int, review: Review) -> dict:
    try:
        return save_review(ROOT, run_id, case_id, review)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Unknown simulation run") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/simulator/runs/{run_id}/replay")
def simulator_replay(run_id: str) -> dict:
    previous = simulator_load(run_id)
    try:
        return generate_run(
            ROOT,
            SimulationRequest(
                set_number=previous["setNumber"],
                count=previous["count"],
                seed=previous["seed"],
            ),
            previous,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
