from collections import Counter

import pytest
from pydantic import ValidationError
from test_scoring import composition, spot

from tft_spot.engine.item_fit import allocate_items, compile_item_context
from tft_spot.engine.scoring import score_composition
from tft_spot.engine.simulator import benchmark_summary
from tft_spot.models.configuration import StrategySettings


def option(item="shojin", recipe=None, holder="unit", category="mana", quality=1):
    return {
        "itemApiName": item,
        "recipe": recipe or ["tear", "sword"],
        "holderApiName": holder,
        "holderFit": quality,
        "targetFit": 1,
        "category": category,
    }


def test_plan_cannot_spend_same_sword_twice_and_uses_duplicate_recipe():
    context = {
        "options": [
            option(),
            option("other", ["sword", "bow"]),
            option("red", ["bow", "bow"], category="antiheal"),
        ]
    }
    plan = allocate_items(context, Counter(tear=1, sword=1, bow=2), Counter(unit=3))
    assert len(plan["plans"]) == 2
    assert {p["itemApiName"] for p in plan["plans"]} == {"shojin", "red"}
    assert plan["fit"] == 100
    one_bow = allocate_items(
        {"options": [context["options"][2]]}, Counter(bow=1), Counter(unit=3)
    )
    assert one_bow["plans"] == []


def test_plan_deduplicates_team_utility_and_respects_three_holder_slots():
    plan = allocate_items(
        {"options": [option("red", ["bow", "bow"], category="antiheal")]},
        Counter(bow=6),
        Counter(unit=3),
    )
    assert len(plan["plans"]) == 1
    plan = allocate_items(
        {"options": [option()]}, Counter(tear=4, sword=4), Counter(unit=3)
    )
    assert len(plan["plans"]) == 3


def test_upgraded_holder_and_missing_holder_and_large_inventory():
    context = {"options": [option()]}
    inventory = Counter(tear=1, sword=1)
    assert (
        allocate_items(context, inventory, Counter(unit=3))["fit"]
        > allocate_items(context, inventory, Counter(unit=2))["fit"]
    )
    assert allocate_items(context, inventory, Counter())["plans"] == []
    assert (
        allocate_items(context, Counter(tear=11), Counter(unit=3))["available"] is False
    )


def test_role_prior_and_explicit_override_precedence():
    catalogs = {
        "champions": {
            "caster": {"name": "Caster", "set": 18, "cost": 1, "role": "Attack Caster"},
            "marksman": {
                "name": "Marksman",
                "set": 18,
                "cost": 1,
                "role": "Attack Marksman",
            },
            "specialist": {
                "name": "Specialist",
                "set": 18,
                "cost": 1,
                "role": "Attack Specialist",
            },
        },
        "items": {
            "DA_SpearOfShojin": {
                "name": "Shojin",
                "set": 18,
                "type": "craftables",
                "composition": ["tear", "sword"],
            },
            "tear": {"type": "components"},
            "sword": {"type": "components"},
        },
    }
    workspace = {
        "source": {"set": 18},
        "configuration": {},
        "finalUnits": [{"apiName": "caster", "items": []}],
        "earlyUnits": [],
    }
    ctx = compile_item_context(workspace, catalogs)
    assert {o["holderApiName"] for o in ctx["options"]} == {"caster"}
    workspace["finalUnits"][0]["items"] = [{"apiName": "DA_SpearOfShojin"}]
    workspace["configuration"] = {
        "strategy": {
            "itemOverrides": [
                {
                    "championApiName": "caster",
                    "itemApiName": "DA_SpearOfShojin",
                    "fit": 0,
                    "reason": "No mana use in this variant",
                }
            ]
        }
    }
    assert compile_item_context(workspace, catalogs)["options"] == []


def test_unknown_augment_separate_from_hard_gate():
    result = score_composition(composition(), spot(offeredAugments=["unknown"]))
    assert result["assessment"] == "unassessed" and result["score"] is None
    blocked = score_composition(
        composition(augments=[{"apiName": "required", "priority": "essential"}]),
        spot(offeredAugments=["unknown"]),
    )
    assert blocked["assessment"] == "blocked"


def test_alternative_opener_does_not_sum_incompatible_units():
    comp = composition(
        strategy={"openers": [{"name": "Alternative", "units": [{"apiName": "other"}]}]}
    )
    result = score_composition(comp, spot(units=[{"apiName": "other", "count": 4}]))
    assert result["evidence"]["opener"]["name"] == "Alternative"
    assert result["resourceFit"]["units"] == 100
    assert len(result["evidence"]["units"]) == 1


def test_augment_condition_requires_both_copies_and_buildable_compatible_item():
    comp = composition(
        itemContext={"options": [option()]},
        strategy={
            "augmentConditions": [
                {
                    "augmentApiName": "combat",
                    "championApiName": "unit",
                    "minCopies": 2,
                    "itemApiName": "shojin",
                    "bonus": 20,
                    "reason": "Pair plus slam",
                }
            ]
        },
    )
    args = {"offeredAugments": ["combat"], "units": [{"apiName": "unit", "count": 2}]}
    missing = score_composition(comp, spot(**args))
    present = score_composition(
        comp, spot(**args, components=[{"apiName": "tear"}, {"apiName": "sword"}])
    )
    assert missing["variants"][0]["dimensionScores"]["augments"] == 50
    assert present["variants"][0]["dimensionScores"]["augments"] == 70
    assert present["score"] == sum(
        present["variants"][0]["weightedContributions"].values()
    )


def test_avoided_component_cannot_gain_plan_credit():
    comp = composition(
        itemContext={"options": [option(recipe=["bow", "bow"])]},
        components=[{"apiName": "bow", "priority": "avoid", "requiredCount": 2}],
    )
    result = score_composition(
        comp,
        spot(
            units=[{"apiName": "unit", "count": 3}],
            components=[{"apiName": "bow", "count": 2}],
        ),
    )
    assert result["resourceFit"]["components"] == 0


def test_expert_settings_reject_duplicate_and_invalid_entries():
    with pytest.raises(ValidationError):
        StrategySettings(
            openers=[{"name": "x", "units": [{"apiName": "a"}, {"apiName": "a"}]}]
        )
    with pytest.raises(ValidationError):
        StrategySettings(
            itemOverrides=[
                {"championApiName": "a", "itemApiName": "b", "fit": 2, "reason": "bad"}
            ]
        )


def test_benchmark_excludes_unlabeled_and_keeps_holdout_separate():
    base = {
        "targetSourceId": "x",
        "spot": {"components": [{"apiName": "bow", "count": 2}]},
        "rankings": [{"sourceId": "x", "eligible": True}],
    }
    cases = [
        base,
        {
            **base,
            "review": {
                "verdict": "about_right",
                "acceptableSourceIds": ["x"],
                "split": "holdout",
            },
        },
    ]
    result = benchmark_summary(cases)
    assert result["calibration"]["top3HitRate"] is None
    assert result["holdout"]["top3HitRate"] == 1
    assert result["holdout"]["reviewedCases"] == 1


def test_final_target_has_only_three_slots_even_with_multiple_holders():
    opts = [{**option(holder=h), "targetApiName": "carry"} for h in ("a", "b")]
    plan = allocate_items(
        {"options": opts}, Counter(tear=4, sword=4), Counter(a=3, b=3)
    )
    assert len(plan["plans"]) == 3
