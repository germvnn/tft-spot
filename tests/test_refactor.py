from __future__ import annotations

import asyncio
import json
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

import pytest
from test_configurator import build_source_fixture
from test_source_refresh import write_snapshot

import tft_spot.configurator.repository as repository_module
from tft_spot.configurator import api
from tft_spot.configurator.repository import (
    ConfigurationRepository,
    ConfiguratorDataError,
)
from tft_spot.configurator.source_refresh import refresh_tft_academy
from tft_spot.models.configuration import StrategySettings


def test_save_rejects_conflicting_aliases_without_replacing_previous_file(
    tmp_path, monkeypatch
):
    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    path = tmp_path / "data/raw/tft_academy/augments.json"
    payload = json.loads(path.read_text())
    payload["augments"].append(
        {
            **payload["augments"][0],
            "apiName": "alias",
            "id": "alias-source",
        }
    )
    path.write_text(json.dumps(payload))
    guide["augments"].append({"apiName": "alias"})
    repo = ConfigurationRepository(tmp_path)
    config = repo.bootstrap_ready_configurations()[0]
    target = tmp_path / "data/curated/set-18/compositions/source-1.json"
    before = target.read_bytes()
    config.augments[1].priority = "high"
    with pytest.raises(ConfiguratorDataError, match="Conflicting priorities"):
        repo.save_configuration("source-1", config)
    assert target.read_bytes() == before
    # Matching aliases remain separate on disk while the compiler can collapse them.
    config.augments[0].priority = "high"
    saved = repo.save_configuration("source-1", config)
    assert [a.api_name for a in saved.augments] == ["DA_Augment", "alias"]


def test_snapshot_reads_and_decodes_shared_collection_once(tmp_path, monkeypatch):
    guide = build_source_fixture(tmp_path)
    raw = tmp_path / "data/raw/tft_academy"
    index_path = raw / "compositions/index.json"
    index = json.loads(index_path.read_text())
    index["compositions"].append(
        {
            **index["compositions"][0],
            "backend_id": "source-2",
        }
    )
    index_path.write_text(json.dumps(index))
    calls = []
    monkeypatch.setattr(
        repository_module,
        "extract_guides",
        lambda payload: calls.append(payload) or [guide, {**guide, "id": "source-2"}],
    )
    repo = ConfigurationRepository(tmp_path)
    expected = [repo.get_workspace(c["sourceId"]) for c in repo.list_compositions()]
    calls.clear()
    reads = Counter()
    original = repo._read_json

    def read(path):
        reads[path] += 1
        return original(path)

    monkeypatch.setattr(repo, "_read_json", read)
    snapshot = repo.load_snapshot()
    actual = [
        repo.get_workspace(c["sourceId"], snapshot=snapshot)
        for c in repo.list_compositions(snapshot)
    ]
    assert actual == expected
    assert len(calls) == 1
    assert all(count == 1 for count in reads.values())
    # A subsequent operation sees a new source snapshot rather than stale cache.
    guide["title"] = "Updated source title"
    assert (
        repo.get_workspace("source-1", snapshot=repo.load_snapshot())["source"]["title"]
        == "Updated source title"
    )


def test_refresh_archives_removed_expert_rules_and_preserves_valid_ones(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        repository_module, "extract_queried_guide", lambda p: p["guide"]
    )
    write_snapshot(tmp_path / "data", [("keep", "recipe")], asset_marker="old")
    repo = ConfigurationRepository(tmp_path)
    config = repo.bootstrap_ready_configurations()[0]
    config.strategy = StrategySettings(
        augmentConditions=[
            {
                "augmentApiName": "DA_Augment",
                "championApiName": "DA_Early",
                "reason": "Keep my manual assessment",
                "bonus": 12,
            }
        ],
        openers=[
            {"name": "Valid opener", "units": [{"apiName": "DA_Early", "core": True}]}
        ],
    )
    repo.save_configuration("keep", config)

    def runner(command, **kwargs):
        data_dir = Path(command[command.index("--data-dir") + 1])
        write_snapshot(data_dir, [("keep", "recipe")], asset_marker="new")
        path = data_dir / "raw/tft_academy/compositions/keep.json"
        payload = json.loads(path.read_text())
        payload["guide"]["augments"] = []
        path.write_text(json.dumps(payload))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    refresh_tft_academy(tmp_path, repo, runner=runner)
    saved = repo.get_workspace("keep")["configuration"]
    assert saved["status"] == "draft"
    assert saved["strategy"]["augmentConditions"] == []
    assert saved["strategy"]["openers"][0]["units"][0]["core"] is True
    assert (
        saved["retiredStrategyRules"][0]["rule"]["reason"]
        == "Keep my manual assessment"
    )
    assert saved["retiredStrategyRules"][0]["rule"]["bonus"] == 12
    assert "listed augment" in saved["retiredStrategyRules"][0]["reason"]
    # Repeating refresh is idempotent and does not erase or duplicate the archive.
    refresh_tft_academy(tmp_path, repo, runner=runner)
    assert repo.get_workspace("keep")["configuration"] == saved


def test_api_reader_waits_until_snapshot_replacement_finishes(tmp_path, monkeypatch):
    monkeypatch.setattr(
        repository_module, "extract_queried_guide", lambda p: p["guide"]
    )
    write_snapshot(tmp_path / "data", [("old", "recipe")], asset_marker="old")
    repo = ConfigurationRepository(tmp_path)
    repo.bootstrap_ready_configurations()
    monkeypatch.setattr(api, "ROOT", tmp_path)
    monkeypatch.setattr(api, "repository", repo)
    real_refresh = refresh_tft_academy

    def runner(command, **kwargs):
        write_snapshot(
            Path(command[command.index("--data-dir") + 1]),
            [("new", "recipe")],
            asset_marker="new",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(
        api,
        "refresh_tft_academy",
        lambda root, repository: real_refresh(root, repository, runner=runner),
    )
    raw_moved, finish_install, reader_started, read_disk = (
        Event(),
        Event(),
        Event(),
        Event(),
    )
    replace = Path.replace
    read_json = repo._read_json

    def intercept_replace(path, target):
        result = replace(path, target)
        if path == repo.raw_dir:
            raw_moved.set()
            assert finish_install.wait(5)
        return result

    def intercept_read(path):
        if reader_started.is_set():
            read_disk.set()
        return read_json(path)

    monkeypatch.setattr(Path, "replace", intercept_replace)
    monkeypatch.setattr(repo, "_read_json", intercept_read)

    def read():
        reader_started.set()
        return api.list_compositions()

    with ThreadPoolExecutor(max_workers=2) as executor:
        refreshing = executor.submit(api.refresh_source)
        try:
            assert raw_moved.wait(5)
            reading = executor.submit(read)
            assert reader_started.wait(5)
            assert not read_disk.wait(0.05)
        finally:
            finish_install.set()
        refreshing.result(timeout=5)
        assert [c["sourceId"] for c in reading.result(timeout=5)["compositions"]] == [
            "new"
        ]


def test_decorated_api_preserves_request_validation():
    # Exercise the ASGI boundary so decorators cannot silently break FastAPI signatures.
    async def request():
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message):
            messages.append(message)

        await api.app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/api/recommendations",
                "raw_path": b"/api/recommendations",
                "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "server": ("test", 80),
                "client": ("test", 123),
            },
            receive,
            send,
        )
        return messages

    messages = asyncio.run(request())
    assert messages[0]["status"] == 422
    assert b"offeredAugments" in messages[1]["body"]
    assert "/api/recommendations" in api.app.openapi()["paths"]
