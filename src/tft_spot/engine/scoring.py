"""Pure, deterministic stage 2-1 matching. See docs/SCORING.md."""

from collections import Counter
from typing import Any

from tft_spot.models.composition import EngineComposition
from tft_spot.models.spot import Spot

PRIORITY_VALUES = {
    "essential": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
    "avoid": 0.0,
}
COPY_SIGNAL = (0, 1, 3, 5, 8)
SUPPORT_SIGNAL_TARGET = 4.0
SIGNAL_PER_UNIT = 8.0
SCORING_VERSION = "stage-2-1-v3.0"


def _score_composition(comp: EngineComposition, spot: Spot) -> dict[str, Any]:
    if comp.set_number != spot.set_number:
        raise ValueError("Composition and spot must belong to the same set")
    copies: Counter[str] = Counter()
    for unit in spot.units:
        copies[unit.api_name] += unit.count * 3 ** (unit.stars - 1)
    owned: Counter[str] = Counter()
    for component in spot.components:
        owned[component.api_name] += component.count
    units: list[dict[str, Any]] = []
    has_core = any(decision.core for decision in comp.units)
    for decision in comp.units:
        count = copies[decision.api_name]
        signal = (
            COPY_SIGNAL[min(count, 4)]
            if has_core
            else (4 + min(count, 4) if count else 0)
        )
        units.append(
            {
                "apiName": decision.api_name,
                "copies": count,
                "core": decision.core,
                "copySignal": signal,
                "points": signal,
            }
        )
    unit_points = sum(entry["points"] for entry in units)
    core_units = [entry for entry in units if entry["core"]]
    support_points = sum(entry["points"] for entry in units if not entry["core"])
    core_count = len(core_units)
    core_share = 1 - 0.25 / core_count if core_count else 0.0
    core_score = (
        100 * sum(entry["points"] for entry in core_units) / (8 * core_count)
        if core_count
        else 0.0
    )
    support_target = (
        SUPPORT_SIGNAL_TARGET if core_count else SIGNAL_PER_UNIT * len(units)
    )
    support_score = (
        min(100.0, 100 * support_points / support_target) if support_target else 0.0
    )
    core_contribution = core_score * core_share
    support_contribution = support_score * (1 - core_share)
    unit_score = core_contribution + support_contribution
    demands = {d.api_name: d for d in comp.components}
    components: list[dict[str, Any]] = []
    for name, count in owned.items():
        demand = demands.get(name)
        matched = min(count, demand.required_count) if demand else 0
        points = matched * PRIORITY_VALUES[demand.priority] if demand else 0.0
        components.append(
            {
                "apiName": name,
                "ownedCount": count,
                "matchedCount": matched,
                "priority": demand.priority if demand else None,
                "points": points,
            }
        )
    component_score = (
        100 * sum(c["points"] for c in components) / sum(owned.values())
        if owned
        else 0.0
    )
    from tft_spot.engine.item_fit import allocate_items

    avoided = {d.api_name for d in comp.components if d.priority == "avoid"}
    context = {
        **comp.item_context,
        "options": [
            o
            for o in comp.item_context.get("options", [])
            if not avoided.intersection(o["recipe"])
        ],
    }
    item_plan = allocate_items(context, owned, copies) if comp.item_context else None
    base_component_score = component_score
    if item_plan and item_plan["available"] and sum(owned.values()) >= 2:
        component_score = 0.75 * component_score + 0.25 * item_plan["fit"]
    decisions = {d.api_name: d.priority for d in comp.augments}
    essential = next(
        (d.api_name for d in comp.augments if d.priority == "essential"), None
    )
    variants: list[dict[str, Any]] = []
    for name in spot.offered_augments:
        priority = decisions.get(name)
        reason = None
        if essential and name != essential:
            reason = "requires_essential_augment"
        elif priority is None:
            reason = "augment_not_listed"
        elif priority == "avoid":
            reason = "augment_avoided"
        augment_score = 100 * PRIORITY_VALUES.get(priority or "avoid", 0.0)
        conditions: list[dict[str, Any]] = []
        for rule in comp.strategy.augment_conditions:
            if rule.augment_api_name != name:
                continue
            copy_match = copies[rule.champion_api_name] >= rule.min_copies
            item_match = rule.item_api_name is None or any(
                option["itemApiName"] == rule.item_api_name
                and option["holderApiName"] == rule.champion_api_name
                for option in (item_plan or {}).get("candidateOptions", [])
            )
            matched = copy_match and item_match
            conditions.append(
                {
                    "reason": rule.reason,
                    "matched": matched,
                    "bonus": rule.bonus if matched else 0,
                    "championApiName": rule.champion_api_name,
                    "itemApiName": rule.item_api_name,
                }
            )
        base_augment_score = augment_score
        adjustment = max(-20, min(20, sum(c["bonus"] for c in conditions)))
        augment_score = max(0, min(100, augment_score + adjustment))
        contributions = {
            "units": unit_score * comp.weights.units / 100,
            "components": component_score * comp.weights.components / 100,
            "augments": augment_score * comp.weights.augments / 100,
        }
        variants.append(
            {
                "augmentApiName": name,
                "priority": priority,
                "eligible": reason is None,
                "reason": reason,
                "assessment": "unassessed"
                if reason == "augment_not_listed"
                else ("blocked" if reason else "assessed"),
                "augmentContext": {
                    "baseFit": base_augment_score,
                    "adjustment": augment_score - base_augment_score,
                    "conditions": conditions,
                },
                "score": sum(contributions.values()) if reason is None else None,
                "dimensionScores": {
                    "units": unit_score,
                    "components": component_score,
                    "augments": augment_score,
                },
                "weightedContributions": contributions,
            }
        )
    eligible = [v for v in variants if v["eligible"]]
    best = max(eligible, key=lambda v: v["score"]) if eligible else None
    return {
        "sourceId": comp.source_id,
        "title": comp.title,
        "assessment": "assessed"
        if best
        else (
            "unassessed"
            if any(v["assessment"] == "unassessed" for v in variants)
            else "blocked"
        ),
        "resourceFit": {"units": unit_score, "components": component_score},
        "eligible": best is not None,
        "score": best["score"] if best else None,
        "bestAugmentApiName": best["augmentApiName"] if best else None,
        "requiredAugmentApiName": essential,
        "variants": variants,
        "evidence": {
            "units": units,
            "unitPoints": unit_points,
            "unitFit": {
                "coreCount": core_count,
                "coreShare": core_share,
                "coreScore": core_score,
                "supportScore": support_score,
                "coreContribution": core_contribution,
                "supportContribution": support_contribution,
                "supportSignalTarget": support_target,
            },
            "components": components,
            "itemPlan": {k: v for k, v in item_plan.items() if k != "candidateOptions"}
            if item_plan
            else None,
            "componentFit": {
                "baseFit": base_component_score,
                "combinedFit": component_score,
                "planShare": 0.25
                if item_plan and item_plan["available"] and sum(owned.values()) >= 2
                else 0,
            },
        },
        "weights": comp.weights.model_dump(),
    }


def score_composition(comp: EngineComposition, spot: Spot) -> dict[str, Any]:
    result = _score_composition(comp, spot)
    options = [("Opener źródłowy", result)]
    for opener in comp.strategy.openers:
        candidate = _score_composition(
            comp.model_copy(update={"units": opener.units}), spot
        )
        options.append((opener.name, candidate))
    name, best = max(options, key=lambda entry: entry[1]["resourceFit"]["units"])
    best["evidence"]["opener"] = {
        "name": name,
        "alternatives": [
            {"name": title, "unitFit": entry["resourceFit"]["units"]}
            for title, entry in options
        ],
    }
    return best


def rank_compositions(
    compositions: list[EngineComposition], spot: Spot
) -> list[dict[str, Any]]:
    results = [score_composition(comp, spot) for comp in compositions]
    # Python's stable sort preserves source order for ties; offer order breaks variant ties.
    return sorted(
        results, key=lambda result: (not result["eligible"], -(result["score"] or 0))
    )
