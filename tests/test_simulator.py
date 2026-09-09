import json
from collections import Counter

import pytest
from test_configurator import build_source_fixture

from tft_spot.configurator import repository as repository_module
from tft_spot.configurator.repository import ConfigurationRepository
from tft_spot.engine.simulator import (
    Review,
    SimulationRequest,
    generate_run,
    list_runs,
    load_run,
    save_review,
)


@pytest.fixture
def simulation_root(tmp_path, monkeypatch):
    guide = build_source_fixture(tmp_path)
    monkeypatch.setattr(repository_module, "extract_queried_guide", lambda _: guide)
    path = tmp_path / "data/raw/tft_academy/augments.json"
    data = json.loads(path.read_text())
    data["augments"][0]["stages"] = ["2-1"]
    path.write_text(json.dumps(data))
    for category, additions in (
        (
            "champions",
            [
                {
                    "apiName": f"DA_Other_{cost}",
                    "name": f"Other {cost}",
                    "id": f"other-{cost}",
                    "set": 18,
                    "cost": cost,
                }
                for cost in (1, 2, 3)
            ],
        ),
        (
            "items",
            [
                {
                    "apiName": f"DA_Component_{letter}",
                    "name": letter,
                    "id": letter,
                    "set": 18,
                    "type": "components",
                    "composition": [],
                }
                for letter in "CDEF"
            ],
        ),
    ):
        path = tmp_path / f"data/raw/tft_academy/{category}.json"
        data = json.loads(path.read_text())
        data[category].extend(additions)
        path.write_text(json.dumps(data))
    ConfigurationRepository(tmp_path).bootstrap_ready_configurations()
    return tmp_path


def test_fifty_cases_are_reproducible_and_leave_input_files_untouched(simulation_root):
    root = simulation_root
    before = {
        str(p): p.read_bytes()
        for folder in ("raw", "curated")
        for p in (root / "data" / folder).rglob("*.json")
    }
    options = SimulationRequest(count=50, seed=42)
    first = generate_run(root, options)
    second = generate_run(root, options)
    assert first["id"] != second["id"]
    assert first["cases"] == second["cases"]
    assert first["inputFingerprint"] == second["inputFingerprint"]
    assert first["compositionBoards"]["source-1"][0]["apiName"] == "DA_Champion"
    assert len(first["cases"]) == 50
    assert len({c["pattern"] for c in first["cases"]}) == 10
    for case in first["cases"]:
        assert len(case["spot"]["offeredAugments"]) == len(
            set(case["spot"]["offeredAugments"])
        )
        assert all(1 <= u["count"] <= 4 for u in case["spot"]["units"])
        components = case["spot"]["components"]
        assert all(c["count"] == 1 for c in components)
        assert len({c["apiName"] for c in components}) == len(components)
        assert len(components) in (1, 2, 3, 5)
        costs = {"DA_Early": 1, **{f"DA_Other_{c}": c for c in (1, 2, 3)}}
        gold = sum(costs[u["apiName"]] * u["count"] for u in case["spot"]["units"])
        assert 7 <= gold <= 14
        assert case["unitGold"] == gold
        assert all(
            r["score"] is None or 0 <= r["score"] <= 100 for r in case["rankings"]
        )
    assert all(
        __import__("pathlib").Path(p).read_bytes() == data for p, data in before.items()
    )
    distribution = Counter(len(c["spot"]["components"]) for c in first["cases"])
    assert distribution[3] == 40
    assert distribution[5] == 5
    assert sorted((distribution[1], distribution[2])) == [2, 3]
    assert len(list_runs(root)) == 2


def test_reviews_survive_reload_and_replay_keeps_spots_and_original_results(
    simulation_root,
):
    root = simulation_root
    run = generate_run(root, SimulationRequest(count=10))
    frozen = root / "data/evaluations/simulator" / (run["id"] + ".json")
    before = frozen.read_bytes()
    review = Review(
        source_id="source-1",
        verdict="too_low",
        expected_unit_fit=75,
        expected_score=80,
        notes="Strong opener",
    )
    save_review(root, run["id"], 1, review)
    saved = load_run(root, run["id"])
    assert saved["cases"][0]["review"]["expectedUnitFit"] == 75
    assert frozen.read_bytes() == before
    replay = generate_run(root, SimulationRequest(count=10), saved)
    assert replay["compositionBoards"] == run["compositionBoards"]
    assert replay["parentRunId"] == run["id"]
    assert [c["spot"] for c in replay["cases"]] == [c["spot"] for c in run["cases"]]
    assert replay["cases"][0]["referenceReview"]["notes"] == "Strong opener"
    assert replay["cases"][0]["review"] is None
    assert (
        replay["cases"][0]["previousScores"]["source-1"]
        == run["cases"][0]["rankings"][0]["score"]
    )
    with pytest.raises(ValueError):
        save_review(root, run["id"], 999, review)
    with pytest.raises(ValueError):
        save_review(root, run["id"], 1, Review(source_id="unknown", verdict="too_low"))
    with pytest.raises(ValueError):
        load_run(root, "../../outside")


def test_simulation_input_limits_and_missing_set(simulation_root):
    with pytest.raises(ValueError):
        SimulationRequest(count=201)
    with pytest.raises(ValueError):
        generate_run(simulation_root, SimulationRequest(set_number=19))


@pytest.mark.parametrize("seed", range(5))
def test_distribution_and_budget_across_seeds(simulation_root, seed):
    run = generate_run(simulation_root, SimulationRequest(count=100, seed=seed))
    assert Counter(len(c["spot"]["components"]) for c in run["cases"]) == {
        1: 5,
        2: 5,
        3: 80,
        5: 10,
    }
    assert all(7 <= c["unitGold"] <= 14 for c in run["cases"])
    assert all(u["count"] <= 4 for c in run["cases"] for u in c["spot"]["units"])


def test_legacy_replay_does_not_apply_new_generation_limits(simulation_root):
    run = generate_run(simulation_root, SimulationRequest(count=1))
    run["generatorVersion"] = "openers-v1"
    run["cases"][0]["spot"]["units"] = [{"apiName": "DA_Early", "stars": 1, "count": 4}]
    run["cases"][0]["spot"]["components"] = [{"apiName": "DA_Component_A", "count": 2}]
    replay = generate_run(simulation_root, SimulationRequest(count=1), run)
    assert replay["generatorVersion"] == "openers-v1"
    assert replay["cases"][0]["spot"] == run["cases"][0]["spot"]


def test_coverage_mode_is_reproducible_contains_duplicates_and_replays_exactly(
    simulation_root,
):
    options = SimulationRequest(mode="coverage", count=20, seed=7)
    first = generate_run(simulation_root, options)
    second = generate_run(simulation_root, options)
    assert first["cases"] == second["cases"]
    assert first["generatorVersion"] == "coverage-v1"
    assert first["benchmark"]["duplicateComponentCases"] > 0
    replay = generate_run(simulation_root, SimulationRequest(count=20), first)
    assert [c["spot"] for c in replay["cases"]] == [c["spot"] for c in first["cases"]]
    assert replay["mode"] == "coverage"


def test_top3_labels_survive_save_and_are_measured_on_replay(simulation_root):
    run = generate_run(simulation_root, SimulationRequest(count=1))
    save_review(
        simulation_root,
        run["id"],
        1,
        Review(
            sourceId="source-1",
            verdict="about_right",
            acceptableSourceIds=["source-1"],
            split="holdout",
        ),
    )
    loaded = load_run(simulation_root, run["id"])
    assert loaded["benchmark"]["holdout"]["reviewedCases"] == 1
    replay = generate_run(simulation_root, SimulationRequest(count=1), loaded)
    assert replay["benchmark"]["holdout"]["reviewedCases"] == 1
    assert replay["cases"][0]["review"] is None
