from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from tft_spot.configurator.repository import (
    CompositionNotFoundError,
    ConfigurationRepository,
    ConfiguratorDataError,
)
from tft_spot.models.configuration import CompositionConfiguration

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
