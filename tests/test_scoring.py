import pytest
from pydantic import ValidationError

from tft_spot.engine.scoring import rank_compositions, score_composition
from tft_spot.models.composition import EngineComposition
from tft_spot.models.configuration import CompositionConfiguration
from tft_spot.models.spot import Spot


def composition(**changes):
    payload = {
        "sourceId": "one",
        "title": "Example",
        "setNumber": 18,
        "status": "ready",
        "units": [{"apiName": "unit", "priority": "essential"}],
        "components": [{"apiName": "bow", "priority": "high", "requiredCount": 2}],
        "augments": [
            {"apiName": "econ", "priority": "high"},
            {"apiName": "combat", "priority": "medium"},
        ],
    }
    payload.update(changes)
    return EngineComposition.model_validate(payload)


def spot(**changes):
    payload = {"setNumber": 18, "offeredAugments": ["econ", "combat", "unlisted"]}
    payload.update(changes)
    return Spot.model_validate(payload)


@pytest.mark.parametrize(
    "copies,points", list(enumerate([0, 5, 6, 7, 8, 8, 8, 8, 8, 8]))
)
def test_copy_curve(copies, points):
    result = score_composition(
        composition(),
        spot(units=[{"apiName": "unit", "count": copies}] if copies else []),
    )
    assert result["evidence"]["unitPoints"] == points
    assert result["variants"][0]["dimensionScores"]["units"] == pytest.approx(
        min(100, points / 8 * 100)
    )


def test_stars_and_duplicate_entries_count_as_copies():
    result = score_composition(
        composition(),
        spot(units=[{"apiName": "unit", "stars": 2}, {"apiName": "unit", "count": 2}]),
    )
    assert result["evidence"]["unitPoints"] == 8
    assert result["evidence"]["units"][0]["copies"] == 5


def test_components_use_owned_inventory_and_cap_duplicate_demand():
    result = score_composition(
        composition(),
        spot(
            components=[
                {"apiName": "bow"},
                {"apiName": "bow", "count": 2},
                {"apiName": "rod"},
            ]
        ),
    )
    assert result["variants"][0]["dimensionScores"]["components"] == 37.5
    assert result["evidence"]["components"][0]["matchedCount"] == 2


def test_best_augment_is_single_choice_and_explains_weighted_sum():
    result = score_composition(
        composition(),
        spot(
            units=[{"apiName": "unit", "stars": 2, "count": 2}],
            components=[{"apiName": "bow", "count": 2}],
        ),
    )
    assert result["bestAugmentApiName"] == "econ"
    assert result["score"] == 85
    assert result["score"] == sum(
        result["variants"][0]["weightedContributions"].values()
    )
    assert result["variants"][2]["reason"] == "augment_not_listed"
    assert result["variants"][2]["score"] is None


def test_essential_augment_gates_even_with_zero_augment_weight():
    comp = composition(
        augments=[
            {"apiName": "core", "priority": "essential"},
            {"apiName": "econ", "priority": "high"},
        ],
        weights={"units": 100, "components": 0, "augments": 0},
    )
    missing = score_composition(comp, spot(units=[{"apiName": "unit", "stars": 3}]))
    assert missing["eligible"] is False
    assert missing["score"] is None
    present = score_composition(comp, spot(offeredAugments=["econ", "core"]))
    assert present["bestAugmentApiName"] == "core"
    assert present["eligible"] is True


def test_essential_components_and_units_do_not_gate():
    comp = composition(
        components=[{"apiName": "bow", "priority": "essential", "requiredCount": 1}]
    )
    assert score_composition(comp, spot())["eligible"] is True


def test_avoid_is_not_recommended():
    result = score_composition(
        composition(augments=[{"apiName": "econ", "priority": "avoid"}]), spot()
    )
    assert result["eligible"] is False
    assert result["variants"][0]["reason"] == "augment_avoided"


def test_ranking_is_stable_and_not_relative_to_candidates():
    first, second = composition(), composition(sourceId="two")
    result = rank_compositions([first, second], spot())
    assert [r["sourceId"] for r in result] == ["one", "two"]
    assert result[0]["score"] == rank_compositions([first], spot())[0]["score"] == 22.5


def test_extra_unowned_components_do_not_lower_score():
    base = composition()
    extra = composition(
        components=[
            *base.components,
            {"apiName": "sword", "priority": "essential", "requiredCount": 10},
        ],
    )
    state = spot(
        units=[{"apiName": "unit", "count": 2}], components=[{"apiName": "bow"}]
    )
    assert (
        score_composition(base, state)["score"]
        == score_composition(extra, state)["score"]
    )


def test_invalid_configs_and_spots():
    with pytest.raises(ValidationError, match="one essential"):
        composition(
            augments=[
                {"apiName": "a", "priority": "essential"},
                {"apiName": "b", "priority": "essential"},
            ]
        )
    with pytest.raises(ValidationError, match="Duplicate"):
        composition(units=[{"apiName": "u", "priority": "high"}] * 2)
    with pytest.raises(ValidationError, match="ready"):
        composition(status="draft")
    with pytest.raises(ValidationError, match="unset"):
        composition(
            components=[{"apiName": "bow", "priority": "unset", "requiredCount": 1}]
        )
    with pytest.raises(ValidationError):
        spot(units=[{"apiName": "unit", "count": -1}])
    with pytest.raises(ValidationError):
        spot(offeredAugments=["econ", "econ"])
    with pytest.raises(ValueError, match="same set"):
        score_composition(composition(), spot(setNumber=17))
    with pytest.raises(ValidationError, match="one essential"):
        CompositionConfiguration(
            sourceId="s",
            setNumber=18,
            components=[],
            augments=[
                {"apiName": "a", "priority": "essential"},
                {"apiName": "b", "priority": "essential"},
            ],
        )


def test_legacy_unit_priority_is_ignored_and_offer_ties_preserve_order():
    comp = composition(
        units=[{"apiName": "unit", "priority": "high"}],
        augments=[
            {"apiName": "combat", "priority": "high"},
            {"apiName": "econ", "priority": "high"},
        ],
    )
    result = score_composition(
        comp, spot(units=[{"apiName": "unit", "stars": 2, "count": 2}])
    )
    assert result["variants"][0]["dimensionScores"]["units"] == 100
    assert result["bestAugmentApiName"] == "econ"


def test_compiler_rejects_stale_decisions_and_keeps_source_id():
    from tft_spot.engine.compiler import compile_workspace

    comp = composition()
    workspace = {
        "source": {"sourceId": "one", "set": 18, "title": "Example"},
        "configuration": comp.model_dump(),
        "earlyUnits": [{"apiName": "unit"}],
        "components": [{"apiName": "bow", "requiredCount": 2}],
        "augments": [{"apiName": "econ"}, {"apiName": "combat"}],
    }
    assert compile_workspace(workspace).source_id == "one"
    workspace["earlyUnits"].append({"apiName": "new"})
    with pytest.raises(ValueError, match="stale units"):
        compile_workspace(workspace)


def core_composition(core_count=1):
    return composition(
        units=[
            {"apiName": f"core-{index}", "core": True} for index in range(core_count)
        ]
        + [{"apiName": f"support-{index}"} for index in range(4)]
    )


def test_veigar_four_copies_and_three_support_singles_gives_37_5_out_of_40():
    comp = core_composition()
    state = spot(
        units=[{"apiName": "core-0", "count": 4}]
        + [{"apiName": f"support-{i}"} for i in range(3)]
    )
    result = score_composition(comp, state)
    assert result["variants"][0]["weightedContributions"]["units"] == 37.5
    assert result["evidence"]["unitFit"]["coreContribution"] == 75
    assert result["evidence"]["unitFit"]["supportContribution"] == 18.75


@pytest.mark.parametrize("count,share", [(1, 0.75), (2, 0.875), (3, 1 - 0.25 / 3)])
def test_core_share_increases_with_configured_core_count(count, share):
    result = score_composition(
        core_composition(count),
        spot(units=[{"apiName": f"core-{i}", "count": 4} for i in range(count)]),
    )
    assert result["evidence"]["unitFit"]["coreShare"] == pytest.approx(share)
    assert result["variants"][0]["weightedContributions"]["units"] == pytest.approx(
        40 * share
    )


def test_missing_core_cannot_be_replaced_by_support_or_extra_copies_of_another_core():
    comp = core_composition(2)
    support = [{"apiName": f"support-{i}", "count": 4} for i in range(4)]
    first = score_composition(
        comp, spot(units=[{"apiName": "core-0", "count": 4}, *support])
    )
    extra = score_composition(
        comp, spot(units=[{"apiName": "core-0", "count": 9}, *support])
    )
    assert first["score"] == extra["score"]
    assert first["evidence"]["unitFit"]["coreScore"] == 50
    assert first["variants"][0]["dimensionScores"]["units"] == 56.25
    no_core = score_composition(comp, spot(units=support))
    assert no_core["variants"][0]["dimensionScores"]["units"] == 12.5


def test_core_full_support_full_reaches_100_empty_inventory_zero():
    comp = core_composition(2)
    state = spot(
        units=[
            {"apiName": "core-0", "count": 4},
            {"apiName": "core-1", "stars": 2, "count": 2},
        ]
        + [{"apiName": f"support-{i}"} for i in range(4)]
    )
    assert (
        score_composition(comp, state)["variants"][0]["dimensionScores"]["units"] == 100
    )
    assert (
        score_composition(comp, spot())["variants"][0]["dimensionScores"]["units"] == 0
    )


def test_boolean_only_unit_config_and_legacy_unset_are_ready():
    for priority in ("unset", "avoid", "essential"):
        comp = composition(units=[{"apiName": "unit", "priority": priority}])
        assert (
            score_composition(comp, spot(units=[{"apiName": "unit", "count": 4}]))[
                "variants"
            ][0]["dimensionScores"]["units"]
            == 100
        )


def test_no_core_each_opener_unit_has_equal_share_and_caps_independently():
    comp = composition(
        units=[{"apiName": name} for name in ("veigar", "kobuko", "reksai", "teemo")]
    )
    alone = score_composition(comp, spot(units=[{"apiName": "veigar", "count": 4}]))
    assert alone["variants"][0]["weightedContributions"]["units"] == 10
    extra = score_composition(comp, spot(units=[{"apiName": "veigar", "count": 9}]))
    assert extra["score"] == alone["score"]
    supported = score_composition(
        comp,
        spot(
            units=[
                {"apiName": "veigar", "count": 4},
                {"apiName": "kobuko"},
                {"apiName": "reksai"},
                {"apiName": "teemo"},
            ]
        ),
    )
    assert supported["variants"][0]["weightedContributions"]["units"] == 28.75
    complete = score_composition(
        comp,
        spot(
            units=[
                {"apiName": name, "count": 4}
                for name in ("veigar", "kobuko", "reksai", "teemo")
            ]
        ),
    )
    assert complete["variants"][0]["weightedContributions"]["units"] == 40


def test_empty_opener_scores_zero_without_division_by_zero():
    result = score_composition(
        composition(units=[]), spot(units=[{"apiName": "unit", "count": 4}])
    )
    assert result["variants"][0]["dimensionScores"]["units"] == 0
