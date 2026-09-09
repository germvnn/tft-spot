import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = runpy.run_path(
    Path(__file__).parents[1] / "scripts" / "download_tft_academy.py"
)
HttpPayload = SCRIPT["HttpPayload"]
download_compositions = SCRIPT["download_compositions"]
extract_guides = SCRIPT["extract_guides"]
from tft_spot.data.tft_academy import extract_queried_guide, unflatten_sveltekit_data


def test_unflatten_sveltekit_data_resolves_nested_references() -> None:
    values = [
        {"queriedGuide": 1},
        {"id": 2, "title": 3, "earlyComp": 4},
        "source-id",
        "Example comp",
        [5],
        {"apiName": 6},
        "DA_18_Example",
    ]

    assert unflatten_sveltekit_data(values) == {
        "queriedGuide": {
            "id": "source-id",
            "title": "Example comp",
            "earlyComp": [{"apiName": "DA_18_Example"}],
        }
    }


def test_extract_queried_guide_skips_unrelated_nodes() -> None:
    payload = {
        "nodes": [
            {"type": "data", "data": [{"patch": 1}, "18.1"]},
            {"type": "data", "data": [{"queriedGuide": 1}, {"id": 2}, "abc"]},
        ]
    }

    assert extract_queried_guide(payload) == {"id": "abc"}


def test_extract_guides_preserves_source_order() -> None:
    payload = {
        "nodes": [
            {
                "type": "data",
                "data": [
                    {"guides": 1},
                    [2, 5],
                    {"id": 3, "title": 4},
                    "primary",
                    "Primary",
                    {"id": 6, "title": 7},
                    "variant",
                    "Variant",
                ],
            }
        ]
    }

    assert extract_guides(payload) == [
        {"id": "primary", "title": "Primary"},
        {"id": "variant", "title": "Variant"},
    ]


def test_download_compositions_indexes_variants_and_hidden_guides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response_body = b'{"nodes":[]}'
    listing_url = "https://example.test/tierlist/comps"
    calls: list[tuple[str, str]] = []

    def fake_fetch(
        url: str,
        *,
        timeout: float,
        retries: int,
        accept: str,
    ) -> object:
        del timeout, retries
        calls.append((url, accept))
        return HttpPayload(
            body=response_body,
            status=200,
            content_type="application/json",
            final_url=url,
        )

    guides = [
        {
            "id": "primary",
            "title": "Primary",
            "compSlug": "set-18-shared",
            "set": 18,
            "isPublic": True,
            "tier": "A",
        },
        {
            "id": "variant",
            "title": "Hidden tier X variant",
            "compSlug": "set-18-shared",
            "set": 18,
            "isPublic": False,
            "tier": "X",
        },
        {
            "id": "empty-slug",
            "title": "Hidden guide without a route",
            "compSlug": "",
            "set": 18,
            "isPublic": False,
            "tier": "X",
        },
        {
            "id": "other-set",
            "title": "Other set",
            "compSlug": "set-17-other",
            "set": 17,
            "isPublic": True,
            "tier": "A",
        },
    ]
    monkeypatch.setitem(download_compositions.__globals__, "fetch", fake_fetch)
    monkeypatch.setitem(
        download_compositions.__globals__,
        "extract_guides",
        lambda _payload: guides,
    )

    entries, guide_resource = download_compositions(
        data_dir=tmp_path / "data",
        listing_url=listing_url,
        set_number=18,
        timeout=1,
        retries=0,
        downloaded_at="2026-09-09T00:00:00Z",
    )

    assert calls == [
        ("https://example.test/tierlist/comps/__data.json", "application/json")
    ]
    assert [
        (entry["backend_id"], entry["slug"], entry["visible_name"]) for entry in entries
    ] == [
        ("primary", "set-18-shared", "Primary"),
        ("variant", "set-18-shared", "Hidden tier X variant"),
        ("empty-slug", "", "Hidden guide without a route"),
    ]
    assert {entry["response_file"] for entry in entries} == {
        "data/raw/tft_academy/compositions/guides.json"
    }
    guide_path = (
        tmp_path / "data" / "raw" / "tft_academy" / "compositions" / "guides.json"
    )
    assert guide_path.read_bytes() == response_body
    index = json.loads(guide_path.with_name("index.json").read_text())
    assert index["compositions"] == entries
    assert index["discovery_request"] == "GET /tierlist/comps/__data.json"
    assert guide_resource["filename"] == "compositions/guides.json"


def test_standalone_downloader_help_needs_no_installed_packages():
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(Path(__file__).parents[1] / "scripts/download_tft_academy.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--skip-assets" in result.stdout
