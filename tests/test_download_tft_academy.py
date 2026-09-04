import runpy
from pathlib import Path

SCRIPT = runpy.run_path(
    Path(__file__).parents[1] / "scripts" / "download_tft_academy.py"
)
extract_composition_slugs = SCRIPT["extract_composition_slugs"]
extract_queried_guide = SCRIPT["extract_queried_guide"]
unflatten_sveltekit_data = SCRIPT["unflatten_sveltekit_data"]


def test_extract_composition_slugs_filters_set_and_preserves_page_order() -> None:
    html = """
    <a href="/tierlist/comps/set17">Set 17</a>
    <a href="/tierlist/comps/set-18-first">First</a>
    <a href='/tierlist/comps/set-18-second'>Second</a>
    <a href="/tierlist/comps/set-18-first">Duplicate</a>
    <a href="/tierlist/comps/set-17-old">Old</a>
    """

    assert extract_composition_slugs(html, 18) == [
        "set-18-first",
        "set-18-second",
    ]


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
